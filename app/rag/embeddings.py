# backend/app/rag/embeddings.py
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union
from app.config import settings

class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
    
    def encode_texts(self, texts: Union[str, List[str]]) -> np.ndarray:
        """Encode text(s) into embeddings"""
        if isinstance(texts, str):
            texts = [texts]
        
        return self.model.encode(texts)
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings"""
        from sklearn.metrics.pairwise import cosine_similarity
        
        if embedding1.ndim == 1:
            embedding1 = embedding1.reshape(1, -1)
        if embedding2.ndim == 1:
            embedding2 = embedding2.reshape(1, -1)
        
        return float(cosine_similarity(embedding1, embedding2)[0][0])
    
    def find_most_similar(self, query_embedding: np.ndarray, 
                         candidate_embeddings: np.ndarray, 
                         top_k: int = 5) -> List[tuple]:
        """Find most similar embeddings with their indices and scores"""
        from sklearn.metrics.pairwise import cosine_similarity
        
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        similarities = cosine_similarity(query_embedding, candidate_embeddings)[0]
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            results.append((int(idx), float(similarities[idx])))
        
        return results