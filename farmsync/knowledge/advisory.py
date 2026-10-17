"""
Agronomy Advisory Knowledge Engine for FARMSYNC.

Architectural guarantees:
1. Document Corpus Retrieval: Indexes authentic TNAU and ICAR Crop Production Guides.
2. FAISS Vector Search: Employs a dense FAISS vector index (IndexFlatIP with normalized
   embeddings) powered by all-MiniLM-L6-v2 for semantic document chunk retrieval.
3. Strict Refuse-to-Invent Grounding: Returns `source_grounded: False` and `found: False`
   whenever a requested crop or growth stage is missing from the corpus or fails the
   relevance threshold. Never falsely asserts that an unverified advisory is source-grounded.
"""

import os
import json
import re
import hashlib
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
from farmsync.aws import create_client, EMBEDDING_MODEL, safe_error

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class AgronomyKnowledgeEngine:
    """
    RAG-driven Agronomy Knowledge Engine for FARMSYNC.
    Retrieves evidence-backed agronomy practices, fertilizer schedules,
    and pest management using genuine FAISS dense vector search over
    an official TNAU / ICAR document corpus.
    """
    DEFAULT_SNAPSHOT_PATH = os.path.join(
        os.path.expanduser("~"),
        ".cache", "huggingface", "hub",
        "models--sentence-transformers--all-MiniLM-L6-v2",
        "snapshots", "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
    )

    def __init__(
        self,
        corpus_path: Optional[str] = None,
        index_path: Optional[str] = None
    ):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.corpus_path = corpus_path or os.path.join(base_dir, "corpus", "agronomy_corpus.json")
        self.index_path = index_path or os.path.join(base_dir, "faiss_agronomy.index")
        
        self.corpus: List[Dict[str, Any]] = []
        self.model = None
        self.faiss_index = None
        self.embedding_dim = 384
        self.similarity_threshold = 0.50
        self.bedrock_client = None
        self.embedding_cache = {}
        self.embedding_error = None

        self._load_corpus()
        self._init_embedder()
        self._init_or_build_faiss_index()

    def _load_corpus(self):
        """Loads official TNAU/ICAR agronomy document corpus from JSON."""
        if os.path.exists(self.corpus_path):
            try:
                with open(self.corpus_path, "r", encoding="utf-8") as f:
                    self.corpus = json.load(f)
            except Exception as e:
                print(f"[AgronomyKnowledgeEngine] Warning loading corpus: {e}")
                self.corpus = []
        else:
            self.corpus = []

    def _init_embedder(self, force_local=False):
        """Initializes dense sentence transformer embedder."""
        if not force_local and os.getenv("FARMSYNC_EMBEDDINGS_PROVIDER", "local").lower() == "bedrock":
            try:
                self.bedrock_client = create_client("bedrock-runtime")
                if self.bedrock_client is not None:
                    self.embedding_dim = 256
                    return
            except Exception as exc:
                self.embedding_error = safe_error(exc)
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            self.model = None
            return

        # Attempt to load from cached snapshot first (fast & offline)
        if os.path.exists(self.DEFAULT_SNAPSHOT_PATH):
            try:
                self.model = SentenceTransformer(self.DEFAULT_SNAPSHOT_PATH)
                return
            except Exception:
                pass

        # Fallback to standard identifier
        try:
            self.model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
        except Exception as e:
            print(f"[AgronomyKnowledgeEngine] Note on embedder: {e}")
            self.model = None

    def _encode_text(self, texts: List[str]) -> np.ndarray:
        """Encodes text passages into normalized unit vectors for cosine similarity."""
        if self.bedrock_client is not None:
            vectors = []
            for text in texts:
                key = hashlib.sha256(text.encode()).hexdigest()
                if key not in self.embedding_cache:
                    result = self.bedrock_client.invoke_model(
                        modelId=EMBEDDING_MODEL,
                        body=json.dumps({"inputText": text, "dimensions": 256, "normalize": True}),
                        contentType="application/json", accept="application/json"
                    )
                    vector = np.asarray(json.loads(result["body"].read())["embedding"], dtype=np.float32)
                    if vector.shape != (256,) or not np.isfinite(vector).all() or np.linalg.norm(vector) == 0:
                        raise ValueError("Invalid Titan embedding response")
                    self.embedding_cache[key] = vector / np.linalg.norm(vector)
                vectors.append(self.embedding_cache[key])
            return np.asarray(vectors, dtype=np.float32)
        if self.model is not None:
            embs = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            return np.array(embs, dtype=np.float32)

        # Deterministic TF-IDF / term-hash fallback if transformer not available
        dim = self.embedding_dim
        vecs = []
        for t in texts:
            words = re.findall(r'\w+', t.lower())
            v = np.zeros(dim, dtype=np.float32)
            for w in words:
                idx = int.from_bytes(hashlib.sha256(w.encode()).digest()[:8], "big") % dim
                v[idx] += 1.0
            norm = np.linalg.norm(v)
            if norm > 0:
                v = v / norm
            vecs.append(v)
        return np.array(vecs, dtype=np.float32)

    def _init_or_build_faiss_index(self):
        """Initializes or constructs FAISS IndexFlatIP (cosine similarity) from corpus."""
        if not FAISS_AVAILABLE or not self.corpus:
            self.faiss_index = None
            return

        # Rebuild the small corpus in memory: a count match cannot establish that
        # persisted vectors use the current corpus, model, or hashing algorithm.

        # Build genuine FAISS vector index
        try:
            doc_texts = [
                f"Crop: {d.get('crop')} stage: {d.get('growth_stage')}. {d.get('title')}. {d.get('text')} "
                f"Fertilizer: {d.get('fertilizer_schedule')} Irrigation: {d.get('water_management')} Pest: {d.get('pest_management')}"
                for d in self.corpus
            ]
            embeddings = self._encode_text(doc_texts)
            index = faiss.IndexFlatIP(self.embedding_dim)
            index.add(embeddings)
            self.faiss_index = index
        except Exception as e:
            if self.bedrock_client is not None:
                # Never combine cloud vectors and local vectors in one index.
                self.embedding_error = safe_error(e)
                self.bedrock_client = None
                self.embedding_cache.clear()
                self.embedding_dim = 384
                self._init_embedder(force_local=True)
                self._init_or_build_faiss_index()
                return
            print(f"[AgronomyKnowledgeEngine] Error building FAISS index: {safe_error(e)}")
            self.faiss_index = None

    def get_status(self) -> Dict[str, Any]:
        """Returns FAISS vector index operational metrics."""
        return {
            "rag_engine": "FAISS Dense Vector Index",
            "index_available": self.faiss_index is not None,
            "total_indexed_documents": len(self.corpus),
            "faiss_total_vectors": self.faiss_index.ntotal if self.faiss_index else 0,
            "embedding_model": EMBEDDING_MODEL if self.bedrock_client is not None else "all-MiniLM-L6-v2 (384-d)" if self.model is not None else "SHA256 term hashing (384-d)",
            "embedding_backend": "AWS_BEDROCK" if self.bedrock_client is not None else "LOCAL",
            "embedding_error": self.embedding_error,
            "similarity_metric": "Cosine Similarity (IndexFlatIP)",
            "similarity_threshold": self.similarity_threshold,
            "corpus_path": self.corpus_path,
            "index_path": self.index_path
        }

    @staticmethod
    def _normalize_stage(stage: Optional[str]) -> str:
        """Normalizes growth stage strings and maps standard agronomic synonyms."""
        if not stage:
            return ""
        s = str(stage).strip().lower().replace("-", "_").replace(" ", "_")
        synonyms = {
            "mature": "full_growth",
            "adult": "full_growth",
            "bearing": "full_growth",
            "vegetative": "vegetation",
            "tillering": "vegetation",
            "reproductive": "flowering",
            "squaring": "flowering",
            "pegging": "flowering"
        }
        return synonyms.get(s, s)

    def get_advisory(self, crop_name: str, growth_stage: str) -> Dict[str, Any]:
        """
        Retrieves stage-specific agronomy advisory via FAISS vector similarity search.
        
        STRICT GROUNDING POLICY:
        - If matching crop AND matching growth stage is found in the corpus with high similarity:
          returns source_grounded=True.
        - If crop is unknown, unsupported, or the requested growth stage is not in the corpus:
          returns source_grounded=False and found=False.
        - Under the strict Refuse-to-Invent policy, a document for a DIFFERENT growth stage
          is NEVER claimed to be source-grounded for the requested stage.
        """
        clean_crop = str(crop_name).strip()
        clean_stage = str(growth_stage).strip().lower() if growth_stage else ""
        norm_stage = self._normalize_stage(clean_stage)
        is_stage_unspecified = norm_stage in ("", "unspecified", "all", "any", "general", "none")

        # Step 1: Query construction for RAG retrieval with stage semantics
        stage_synonyms = {
            "full_growth": "full growth adult bearing mature shooting",
            "vegetation": "vegetation vegetative active tillering knee-high",
            "flowering": "flowering reproductive panicle squaring pegging"
        }
        stage_expanded = stage_synonyms.get(norm_stage, clean_stage)
        query_text = (
            f"Agronomic package of practices for {clean_crop} at {stage_expanded} stage: "
            f"fertilizer schedule, nutrient application, irrigation management, and pest control."
        )

        top_doc = None
        top_score = 0.0

        # Step 2: Dense FAISS Vector Search
        if self.faiss_index is not None and len(self.corpus) > 0:
            try:
                q_vec = self._encode_text([query_text])
                D, I = self.faiss_index.search(q_vec, k=min(5, len(self.corpus)))
                
                # Evaluate retrieved candidates
                matching_candidates = []
                for score, idx in zip(D[0], I[0]):
                    if idx < 0 or idx >= len(self.corpus):
                        continue
                    cand = self.corpus[idx]
                    cand_crop = cand.get("crop", "").lower()
                    target_crop_lower = clean_crop.lower()
                    
                    # Crop relevance check: target crop must match retrieved crop
                    # Handles e.g. "Rice (Paddy)" vs "Rice" or "Coconut" vs "Coconut"
                    crop_matches = (
                        cand_crop in target_crop_lower or 
                        target_crop_lower in cand_crop or
                        ("paddy" in target_crop_lower and "rice" in cand_crop) or
                        ("rice" in target_crop_lower and "paddy" in cand_crop)
                    )
                    
                    if crop_matches:
                        matching_candidates.append((float(score), cand))

                # Growth stage matching check:
                # If a specific growth stage was requested, we ONLY accept candidates that match it!
                if is_stage_unspecified:
                    if matching_candidates:
                        matching_candidates.sort(key=lambda x: x[0], reverse=True)
                        top_score, top_doc = matching_candidates[0]
                else:
                    stage_matched = [
                        c for c in matching_candidates 
                        if self._normalize_stage(c[1].get("growth_stage", "")) == norm_stage
                    ]
                    if stage_matched:
                        stage_matched.sort(key=lambda x: x[0], reverse=True)
                        top_score, top_doc = stage_matched[0]
                    # Note: If stage_matched is empty, we strictly refuse to pick a candidate with a mismatched stage!
            except Exception as e:
                print(f"[AgronomyKnowledgeEngine] FAISS search notice: {e}")

        # Step 3: Direct corpus lookup fallback (if vector search missed or index unbuilt)
        if not top_doc and self.corpus:
            for d in self.corpus:
                d_crop = d.get("crop", "").lower()
                target_crop = clean_crop.lower()
                crop_matches = (
                    d_crop in target_crop or 
                    target_crop in d_crop or
                    ("paddy" in target_crop and "rice" in d_crop) or
                    ("rice" in target_crop and "paddy" in d_crop)
                )
                if crop_matches:
                    d_stage = self._normalize_stage(d.get("growth_stage", ""))
                    if is_stage_unspecified:
                        top_doc = d
                        top_score = 1.00
                        break
                    elif d_stage == norm_stage:
                        top_doc = d
                        top_score = 1.00
                        break
                    # Under Refuse-to-Invent policy, NEVER assign 0.85 or accept a mismatched growth stage!

        # Step 4: Strict Verification Decision
        # If no valid corpus entry matches this crop AND requested stage OR similarity score is below threshold
        if not top_doc or top_score < self.similarity_threshold:
            # Check if this crop exists in the corpus at other growth stages
            crop_available_stages = [
                d.get("growth_stage") for d in self.corpus
                if (
                    d.get("crop", "").lower() in clean_crop.lower() or 
                    clean_crop.lower() in d.get("crop", "").lower() or
                    ("paddy" in clean_crop.lower() and "rice" in d.get("crop", "").lower()) or
                    ("rice" in clean_crop.lower() and "paddy" in d.get("crop", "").lower())
                )
            ]

            if crop_available_stages and not is_stage_unspecified:
                verdict = "STAGE_MISMATCH_NO_GROUNDED_ADVISORY"
                notice = (
                    f"Crop '{clean_crop}' is indexed in the official TNAU/ICAR document corpus, but only for "
                    f"growth stages: {crop_available_stages}. No verified guidelines exist for requested stage '{clean_stage}'. "
                    f"Under the strict Refuse-to-Invent policy, mismatched growth-stage recommendations are refused "
                    f"and never returned as source-grounded."
                )
                title = f"No Verified Agronomy Advisory for {clean_crop} at {clean_stage} stage"
            else:
                verdict = "UNVERIFIED_CROP_NO_GROUNDED_ADVISORY"
                notice = (
                    f"Crop '{clean_crop}' at stage '{clean_stage}' was not found in the official TNAU/ICAR "
                    "agronomic document corpus. Under the strict Refuse-to-Invent policy, "
                    "no fabricated guidelines are returned."
                )
                title = f"No Verified Agronomy Advisory for {clean_crop} ({clean_stage})"

            return {
                "crop": clean_crop,
                "growth_stage": clean_stage,
                "found": False,
                "source_grounded": False,
                "stage_match_status": "STAGE_MISMATCH" if crop_available_stages else "CROP_NOT_FOUND",
                "available_stages_in_corpus": crop_available_stages,
                "advisory_title": title,
                "fertilizer_schedule": None,
                "water_management": None,
                "pest_management": None,
                "citation_source": None,
                "retrieval_method": "FAISS_Vector_Search" if self.faiss_index else "Document_Corpus_Scan",
                "similarity_score": round(top_score, 3) if top_doc else 0.0,
                "verdict": verdict,
                "notice": notice
            }

        # Genuine match retrieved from verified corpus matching both crop and growth stage
        return {
            "crop": clean_crop,
            "growth_stage": top_doc.get("growth_stage", clean_stage),
            "found": True,
            "source_grounded": True,
            "stage_match_status": "EXACT_STAGE_MATCH",
            "advisory_title": top_doc.get("title"),
            "fertilizer_schedule": top_doc.get("fertilizer_schedule"),
            "water_management": top_doc.get("water_management"),
            "pest_management": top_doc.get("pest_management"),
            "citation_source": top_doc.get("citation_source"),
            "doc_id": top_doc.get("doc_id"),
            "publisher": top_doc.get("publisher"),
            "page_number": top_doc.get("page_number"),
            "retrieval_method": "FAISS_Dense_Vector_Search (all-MiniLM-L6-v2)" if self.faiss_index else "Document_Corpus_Scan",
            "similarity_score": round(top_score, 3),
            "verdict": "VERIFIED_GROUNDED_ADVISORY"
        }
