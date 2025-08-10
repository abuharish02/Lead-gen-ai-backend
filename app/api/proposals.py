from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime

from app.database import get_db, COLLECTIONS
from app.utils.auth import get_current_active_user
from app.services.gemini_client import GeminiClient
from app.rag.retrieval import RetrievalService


router = APIRouter(dependencies=[Depends(get_current_active_user)])


class ProposalRequest(BaseModel):
    analysis_id: str = Field(..., description="ID of the completed analysis to base the proposal on")
    kind: Literal["email", "proposal"] = Field("email", description="Type of content to generate")
    service_focus: Optional[str] = Field(
        None,
        description="Optional service focus, e.g., 'website modernization', 'SEO', 'cloud migration'"
    )
    tone: Optional[Literal["friendly", "professional", "bold"]] = Field(
        "professional", description="Tone for generated content (email only)"
    )
    call_to_action: Optional[str] = Field(
        None, description="Optional explicit CTA to include (email only)"
    )


class BulkProposalRequest(BaseModel):
    analysis_ids: List[str] = Field(..., description="List of completed analysis IDs")
    kind: Literal["email", "proposal"] = "email"
    service_focus: Optional[str] = None
    tone: Optional[Literal["friendly", "professional", "bold"]] = "professional"
    call_to_action: Optional[str] = None


def _normalize_analysis_for_generation(analysis_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten and normalize analysis data for generation calls."""
    result = analysis_doc.get("result_data", {}) or {}
    result["company_name"] = analysis_doc.get("company_name") or result.get("company_name")
    result["industry"] = analysis_doc.get("industry") or result.get("industry")
    result["url"] = analysis_doc.get("url")
    return result


@router.post("/proposals/generate", response_model=Dict[str, Any])
async def generate_proposal(payload: ProposalRequest, db=Depends(get_db)):
    """Generate an outreach email or proposal content for a single completed analysis."""
    try:
        analysis = await db[COLLECTIONS["analyses"]].find_one({"_id": ObjectId(payload.analysis_id)})
        if not analysis or analysis.get("status") != "completed":
            raise HTTPException(status_code=404, detail="Completed analysis not found")

        base_analysis = _normalize_analysis_for_generation(analysis)

        # Build a retrieval query using available fields
        query_parts = [
            base_analysis.get("company_name") or "",
            base_analysis.get("industry") or "",
            ", ".join(base_analysis.get("technologies", []) or []),
            ", ".join(base_analysis.get("pain_points", []) or []),
            payload.service_focus or "",
        ]
        retrieval_query = " | ".join([p for p in query_parts if p])

        # Enhance with RAG context
        retriever = RetrievalService()
        rag_context = await retriever.retrieve_context(retrieval_query, context_type="proposal")

        gemini = GeminiClient()
        enhanced_analysis = gemini.enhance_analysis_with_rag(base_analysis, rag_context)
        # If enhancement failed, fall back to base
        effective_analysis = enhanced_analysis if isinstance(enhanced_analysis, dict) and not enhanced_analysis.get("error") else base_analysis

        if payload.kind == "email":
            content = gemini.generate_targeted_outreach(effective_analysis, template_type="email")
            # Add optional tone/CTA hints if model returns raw JSON only
            if isinstance(content, dict) and not content.get("error"):
                if payload.call_to_action and not content.get("call_to_action"):
                    content["call_to_action"] = payload.call_to_action
                # Optionally annotate tone for the client to display
                content["tone"] = payload.tone
        else:
            # Detailed proposal
            focus = payload.service_focus or "Comprehensive digital solutions"
            content = gemini.generate_proposal_content(effective_analysis, service_focus=focus)

        if not isinstance(content, dict) or content.get("error"):
            raise HTTPException(status_code=500, detail=content.get("error", "Generation failed"))

        # Mark lead tracking as proposal generated
        try:
            await db[COLLECTIONS["analyses"]].update_one(
                {"_id": ObjectId(payload.analysis_id)},
                {
                    "$set": {
                        "tracking.proposal_generated": True,
                        "tracking.stage": "proposal_generated",
                        "tracking.updated_at": datetime.utcnow(),
                    },
                    "$setOnInsert": {"tracking.created_at": datetime.utcnow()},
                }
            )
        except Exception:
            # Do not fail generation if tracking update fails; just proceed
            pass

        return {
            "analysis_id": payload.analysis_id,
            "company_name": effective_analysis.get("company_name"),
            "website": effective_analysis.get("url"),
            "kind": payload.kind,
            "service_focus": payload.service_focus,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "content": content,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate content: {str(e)}")


@router.post("/proposals/generate/bulk", response_model=Dict[str, Any])
async def generate_bulk_proposals(payload: BulkProposalRequest, db=Depends(get_db)):
    """Generate outreach/proposals for multiple completed analyses."""
    try:
        results: List[Dict[str, Any]] = []
        failures: List[Dict[str, str]] = []

        for analysis_id in payload.analysis_ids:
            try:
                single_payload = ProposalRequest(
                    analysis_id=analysis_id,
                    kind=payload.kind,
                    service_focus=payload.service_focus,
                    tone=payload.tone,
                    call_to_action=payload.call_to_action,
                )
                item = await generate_proposal(single_payload, db)
                results.append(item)
            except HTTPException as exc:
                failures.append({"analysis_id": analysis_id, "error": exc.detail if isinstance(exc.detail, str) else str(exc.detail)})
            except Exception as exc:
                failures.append({"analysis_id": analysis_id, "error": str(exc)})

        return {
            "kind": payload.kind,
            "count": len(results),
            "results": results,
            "failures": failures,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk generation failed: {str(e)}")


