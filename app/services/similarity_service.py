"""Semantic Incident Similarity Retrieval using Sentence-Transformers and FAISS."""

import json
from pathlib import Path
from typing import Any, Dict, List
import faiss
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from app.core.logging import logger


class IncidentSimilarityService:
    """Retrieves similar historical incidents and past engineering resolutions using FAISS."""

    def __init__(self):
        self.artifacts_dir = Path(settings.ML_ARTIFACTS_DIR)
        self.index_path = self.artifacts_dir / "faiss_index.bin"
        self.corpus_path = self.artifacts_dir / "historical_incidents.json"
        self.index = None
        self.corpus: List[Dict[str, Any]] = []
        self.model = None
        self._load_resources()

    def _load_resources(self):
        try:
            if self.index_path.exists() and self.corpus_path.exists():
                self.index = faiss.read_index(str(self.index_path))
                with open(self.corpus_path, "r", encoding="utf-8") as f:
                    self.corpus = json.load(f)
            else:
                logger.warning(f"FAISS index or corpus not found at {self.artifacts_dir}. Run embedding build first.")

            # Load SentenceTransformer model
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as exc:
            logger.error(f"Error initializing IncidentSimilarityService: {exc}")

    def find_similar_incidents(self, incident_query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Encode query and retrieve top_k similar historical incidents from FAISS index.
        """
        if self.index is None or not self.corpus or self.model is None:
            self._load_resources()
            if self.index is None or not self.corpus or self.model is None:
                return []

        # Encode and normalize query vector for cosine similarity
        query_vector = self.model.encode([incident_query], convert_to_numpy=True, normalize_embeddings=True)
        scores, indices = self.index.search(query_vector, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(self.corpus):
                matched = self.corpus[idx]
                results.append({
                    "incident_id": matched.get("incident_id", f"INC-{idx}"),
                    "title": matched.get("title", "Historical Incident"),
                    "similarity_score": round(float(score), 4),
                    "category": matched.get("category", "General"),
                    "summary": matched.get("summary", ""),
                    "resolution": matched.get("resolution", "No historical resolution documented."),
                })

        return results
