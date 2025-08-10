from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from jose import jwt, JWTError
from app.database import get_db, COLLECTIONS
from app.models.user import (
    User,
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    TokenData,
    UserUpdate,
)
from app.utils.auth import (
    get_password_hash,
    verify_password,
    create_tokens,
    get_current_active_user,
)
from app.config import settings
from bson import ObjectId
from typing import List


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(payload: UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    existing = await db[COLLECTIONS["users"]].find_one({"email": payload.email.lower().strip()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = get_password_hash(payload.password)
    user_doc = User(
        email=payload.email.lower().strip(),
        name=payload.name.strip(),
        hashed_password=hashed_pw,
        is_active=True,
        is_verified=True,  # mark verified for simplicity
        created_at=datetime.utcnow(),
        last_login=None,
    ).model_dump(by_alias=True)

    result = await db[COLLECTIONS["users"]].insert_one(user_doc)
    created = await db[COLLECTIONS["users"]].find_one({"_id": result.inserted_id})

    return UserResponse(
        id=str(created["_id"]),
        email=created["email"],
        name=created["name"],
        is_active=created.get("is_active", True),
        is_verified=created.get("is_verified", False),
        created_at=created.get("created_at", datetime.utcnow()),
        last_login=created.get("last_login"),
        last_seen_at=created.get("last_seen_at"),
    )


@router.post("/login", response_model=Token)
async def login_user(payload: UserLogin, db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await db[COLLECTIONS["users"]].find_one({"email": payload.email.lower().strip()})
    if not user or not verify_password(payload.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="User account is inactive")

    # update last_login
    await db[COLLECTIONS["users"]].update_one({"_id": user["_id"]}, {"$set": {"last_login": datetime.utcnow()}})

    tokens = create_tokens(user_id=str(user["_id"]), email=user["email"])
    return Token(**tokens)
def _ensure_admin(current: TokenData):
    if (current.email or '').lower() != settings.ADMIN_EMAIL.lower():
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current: TokenData = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    _ensure_admin(current)
    cursor = db[COLLECTIONS["users"]].find({})
    users = []
    async for u in cursor:
        users.append(UserResponse(
            id=str(u["_id"]),
            email=u["email"],
            name=u.get("name", ""),
            is_active=u.get("is_active", True),
            is_verified=u.get("is_verified", False),
            created_at=u.get("created_at", datetime.utcnow()),
            last_login=u.get("last_login"),
            last_seen_at=u.get("last_seen_at"),
        ))
    return users


@router.get("/users/count")
async def count_users(
    current: TokenData = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    _ensure_admin(current)
    total = await db[COLLECTIONS["users"]].count_documents({})
    return {"count": total}


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user_admin(
    payload: UserCreate,
    current: TokenData = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    _ensure_admin(current)
    existing = await db[COLLECTIONS["users"]].find_one({"email": payload.email.lower().strip()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = get_password_hash(payload.password)
    user_doc = User(
        email=payload.email.lower().strip(),
        name=payload.name.strip(),
        hashed_password=hashed_pw,
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
        last_login=None,
    ).model_dump(by_alias=True)
    result = await db[COLLECTIONS["users"]].insert_one(user_doc)
    created = await db[COLLECTIONS["users"]].find_one({"_id": result.inserted_id})
    return UserResponse(
        id=str(created["_id"]),
        email=created["email"],
        name=created["name"],
        is_active=created.get("is_active", True),
        is_verified=created.get("is_verified", False),
        created_at=created.get("created_at", datetime.utcnow()),
        last_login=created.get("last_login"),
    )


@router.post("/users/{user_id}/logout")
async def force_logout_user(
    user_id: str,
    current: TokenData = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    _ensure_admin(current)
    user = await db[COLLECTIONS["users"]].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db[COLLECTIONS["users"]].update_one(
        {"_id": user["_id"]},
        {"$set": {"token_invalidated_at": datetime.utcnow()}}
    )
    return {"detail": "User logged out"}


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("user_id")
        email = payload.get("sub")
        if not user_id or not email:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    return Token(**create_tokens(user_id=user_id, email=email))


@router.get("/me", response_model=UserResponse)
async def get_me(
    current: TokenData = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user = await db[COLLECTIONS["users"]].find_one({"_id": ObjectId(current.user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        name=user.get("name", ""),
        is_active=user.get("is_active", True),
        is_verified=user.get("is_verified", False),
        created_at=user.get("created_at", datetime.utcnow()),
        last_login=user.get("last_login"),
        last_seen_at=user.get("last_seen_at"),
    )


@router.patch("/me", response_model=UserResponse)
async def update_me(
    payload: UserUpdate,
    current: TokenData = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user = await db[COLLECTIONS["users"]].find_one({"_id": ObjectId(current.user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updates = {}
    # Update display name
    if payload.name is not None and payload.name.strip() and payload.name.strip() != user.get("name", ""):
        updates["name"] = payload.name.strip()

    # Change password if both fields provided and current is valid
    if payload.new_password:
        if not payload.current_password:
            raise HTTPException(status_code=400, detail="Current password required to set new password")
        if not verify_password(payload.current_password, user.get("hashed_password", "")):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        updates["hashed_password"] = get_password_hash(payload.new_password)

    if updates:
        await db[COLLECTIONS["users"]].update_one({"_id": user["_id"]}, {"$set": updates})
        user.update(updates)

    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        name=user.get("name", ""),
        is_active=user.get("is_active", True),
        is_verified=user.get("is_verified", False),
        created_at=user.get("created_at", datetime.utcnow()),
        last_login=user.get("last_login"),
        last_seen_at=user.get("last_seen_at"),
    )

