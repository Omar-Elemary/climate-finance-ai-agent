"""Week 1 hybrid retriever: BM25 + pgvector + RRF + cross-encoder re-rank.

All heavy resources (embedding models, BM25 index, Postgres connection)
are loaded LAZILY on first use — importing this module never downloads
models, never touches the database, and never raises.

Graceful degradation:
- Full path (bm25_index.pkl + Postgres/pgvector available):
  BM25 + vector -> RRF merge -> hydrate from DB -> cross-encoder re-rank.
- Degraded path (no pkl and/or no DB):
  BM25 built in-memory from data/chunks/master_chunks.json (+ optional
  cross-encoder re-rank on text, which needs no ID alignment).
- Last resort: bm25_only_search() — pure lexical, needs only
  rank_bm25 + master_chunks.json (no torch, no Postgres).


"""

import json
import logging
import pickle
import string
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent
BM25_PATH = ROOT / "bm25_index.pkl"
CHUNKS_PATH = ROOT / "data" / "chunks" / "master_chunks.json"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "climate_rag",
    "user": "postgres",
    "password": "postgres",
}

# Module-level caches — populated on first use, never at import.
_cache: dict = {}


def tokenize(text: str) -> list:
    """Helper function to clean text for BM25 matching."""
    text = text.lower()
    return text.translate(str.maketrans("", "", string.punctuation)).split()


# ---------------------------------------------------------------------------
# Lazy resource loaders
# ---------------------------------------------------------------------------

def _load_chunks() -> list:
    """Read master_chunks.json once (fallback corpus for BM25 + hydration)."""
    if "chunks" not in _cache:
        if not CHUNKS_PATH.exists():
            raise RuntimeError(
                f"Chunk corpus not found at {CHUNKS_PATH}. "
                "Run chunker.py first (scraper.py -> chunker.py)."
            )
        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            _cache["chunks"] = json.load(f)
        logger.info("Loaded %d chunks from %s", len(_cache["chunks"]), CHUNKS_PATH)
    return _cache["chunks"]


def _chunks_by_id() -> dict:
    if "chunks_by_id" not in _cache:
        _cache["chunks_by_id"] = {c["chunk_id"]: c for c in _load_chunks()}
    return _cache["chunks_by_id"]


def _get_bm25():
    """Return (bm25_model, bm25_ids).

    Prefers the prebuilt bm25_index.pkl; otherwise builds an in-memory
    BM25Okapi from master_chunks.json (slower first call, no torch needed).
    """
    if "bm25" not in _cache:
        try:
            from rank_bm25 import BM25Okapi
        except ImportError as e:
            raise RuntimeError(
                "rank_bm25 is not installed. Run: pip install rank_bm25"
            ) from e
        if BM25_PATH.exists():
            with open(BM25_PATH, "rb") as f:
                bm25_data = pickle.load(f)
            _cache["bm25"] = (bm25_data["bm25_index"], bm25_data["chunk_ids"])
            logger.info("Loaded prebuilt BM25 index from %s", BM25_PATH)
        else:
            logger.warning(
                "bm25_index.pkl not found — building in-memory BM25 from %s "
                "(run embedder.py to prebuild it).", CHUNKS_PATH,
            )
            chunks = _load_chunks()
            tokenized = [tokenize(c.get("text", "")) for c in chunks]
            ids = [c["chunk_id"] for c in chunks]
            _cache["bm25"] = (BM25Okapi(tokenized), ids)
    return _cache["bm25"]


def _get_embedder():
    """Lazy SentenceTransformer. Raises RuntimeError with fix hints."""
    if "embedder" not in _cache:
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as e:
            raise RuntimeError(
                "Could not import sentence_transformers "
                f"({e}). This is the 'PreTrainedModel' failure: your "
                "torch/torchvision/transformers/sentence-transformers "
                "versions are incompatible. Fix with e.g.: "
                "pip install -U sentence-transformers transformers torch torchvision "
                "(CPU-only torch: pip install torch torchvision "
                "--index-url https://download.pytorch.org/whl/cpu). "
                "BM25-only retrieval still works without it."
            ) from e
        try:
            _cache["embedder"] = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            raise RuntimeError(
                f"Could not load embedding model all-MiniLM-L6-v2 ({e}). "
                "Check torch/transformers compatibility (see above). "
                "BM25-only retrieval still works without it."
            ) from e
    return _cache["embedder"]


def _get_cross_encoder():
    """Lazy CrossEncoder. Returns None (with warning) if unavailable —
    callers fall back to RRF order instead of neural re-ranking."""
    if "cross_encoder" not in _cache:
        try:
            from sentence_transformers import CrossEncoder
            _cache["cross_encoder"] = CrossEncoder(
                "cross-encoder/ms-marco-MiniLM-L-6-v2"
            )
        except Exception as e:
            logger.warning(
                "Cross-encoder unavailable (%s). Falling back to RRF order "
                "without neural re-ranking.", e,
            )
            _cache["cross_encoder"] = None
    return _cache["cross_encoder"]


def _get_db():
    """Lazy Postgres+pgvector connection. Raises RuntimeError if unreachable."""
    if "db" not in _cache:
        try:
            import psycopg2
            from pgvector.psycopg2 import register_vector
        except ImportError as e:
            raise RuntimeError(
                f"Postgres driver missing ({e}). Run: "
                "pip install psycopg2-binary pgvector"
            ) from e
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            register_vector(conn)
            _cache["db"] = conn
            _cache["cursor"] = conn.cursor()
            logger.info("Connected to Postgres %s", DB_CONFIG["database"])
        except Exception as e:
            raise RuntimeError(
                f"Postgres connection failed ({e}). For vector search: "
                "install Postgres + pgvector, create DB 'climate_rag', run "
                "setup_postgres.py then embedder.py. "
                "BM25-only retrieval still works without it."
            ) from e
    return _cache["db"], _cache["cursor"]


def get_chunk_data(id_list: list) -> dict:
    """Fetch text and source URLs from PostgreSQL (legacy helper)."""
    if not id_list:
        return {}
    _, cursor = _get_db()
    format_strings = ",".join(["%s"] * len(id_list))
    cursor.execute(
        f"SELECT id, source_url, chunk_text FROM climate_docs "
        f"WHERE id IN ({format_strings})",
        tuple(id_list),
    )
    return {
        row[0]: {"source_url": row[1], "chunk_text": row[2]}
        for row in cursor.fetchall()
    }


# ---------------------------------------------------------------------------
# Search entry points
# ---------------------------------------------------------------------------

def _hydrate(ids: list) -> dict:
    """Resolve chunk IDs to {source_url, chunk_text}.

    Prefers Postgres (integer IDs from the prebuilt index); falls back to
    master_chunks.json (string chunk_ids from the in-memory index).
    """
    if not ids:
        return {}
    if BM25_PATH.exists():
        try:
            return get_chunk_data(ids)
        except Exception as e:
            logger.warning("DB hydration failed (%s); using chunks file.", e)
    by_id = _chunks_by_id()
    out = {}
    for cid in ids:
        c = by_id.get(cid)
        if c:
            out[cid] = {
                "source_url": c.get("source_url", "Unknown"),
                "chunk_text": c.get("text", ""),
            }
    return out


def _rerank(query: str, candidate_ids: list, chunk_map: dict) -> list:
    """Cross-encoder re-rank if available, else keep RRF order (score=0.0)."""
    cross_encoder = _get_cross_encoder()
    if cross_encoder is None:
        return [(cid, 0.0) for cid in candidate_ids]
    pairs = [[query, chunk_map[cid]["chunk_text"]] for cid in candidate_ids
             if cid in chunk_map]
    if not pairs:
        return []
    scores = cross_encoder.predict(pairs)
    ranked = sorted(
        zip([cid for cid in candidate_ids if cid in chunk_map], scores),
        key=lambda x: x[1], reverse=True,
    )
    return [(cid, float(s)) for cid, s in ranked]


def hybrid_search_with_metadata(query: str, top_k=30, rrf_k=60, final_k=3) -> list:
    """Dual search (BM25 + vector when available), RRF merge, re-rank.

    Degrades gracefully: without torch/Postgres it becomes
    BM25 retrieval + optional cross-encoder re-rank instead of raising.
    """
    bm25_model, bm25_ids = _get_bm25()

    # --- STAGE 1A: BM25 lexical (always available) ---
    tokenized_query = tokenize(query)
    bm25_scores = bm25_model.get_scores(tokenized_query)
    bm25_results = [
        item[0] for item in
        sorted(zip(bm25_ids, bm25_scores), key=lambda x: x[1], reverse=True)[:top_k]
    ]

    # --- STAGE 1B: vector semantic (optional) ---
    # Only valid when the prebuilt index exists, because only then do the
    # BM25 integer IDs and the Postgres integer IDs share one ID space.
    vector_results: list = []
    if BM25_PATH.exists():
        try:
            embedder = _get_embedder()
            _, cursor = _get_db()
            query_vector = embedder.encode(query).tolist()
            cursor.execute(
                "SELECT id FROM climate_docs "
                "ORDER BY embedding <=> %s::vector LIMIT %s;",
                (query_vector, top_k),
            )
            vector_results = [row[0] for row in cursor.fetchall()]
        except RuntimeError as e:
            logger.warning("Vector search skipped: %s", e)
    else:
        logger.info("No prebuilt index — skipping vector search (BM25 + rerank).")

    # --- STAGE 2: RRF merge (top 20 candidates) ---
    rrf_scores: dict = {}
    for rank, chunk_id in enumerate(bm25_results):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (rrf_k + rank + 1)
    for rank, chunk_id in enumerate(vector_results):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (rrf_k + rank + 1)
    candidate_ids = [
        item[0] for item in
        sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:20]
    ]

    # --- STAGE 3+4: hydrate + re-rank ---
    chunk_map = _hydrate(candidate_ids)
    reranked = _rerank(query, candidate_ids, chunk_map)[:final_k]

    return [
        {
            "id": cid,
            "source_url": chunk_map[cid]["source_url"],
            "chunk_text": chunk_map[cid]["chunk_text"],
            "rerank_score": float(score),
        }
        for cid, score in reranked if cid in chunk_map
    ]


def bm25_only_search(query: str, final_k: int = 3) -> list:
    """Pure lexical fallback: needs only rank_bm25 + master_chunks.json.

    No torch, no transformers, no Postgres. Used by RetrievalTool when the
    neural stages are unavailable (e.g. Hanaa's PreTrainedModel env issue).
    """
    bm25_model, bm25_ids = _get_bm25()
    scores = bm25_model.get_scores(tokenize(query))
    top = sorted(zip(bm25_ids, scores), key=lambda x: x[1], reverse=True)[:final_k]
    chunk_map = _hydrate([cid for cid, _ in top])
    return [
        {
            "id": cid,
            "source_url": chunk_map[cid]["source_url"],
            "chunk_text": chunk_map[cid]["chunk_text"],
            "rerank_score": float(score),
        }
        for cid, score in top if cid in chunk_map
    ]


if __name__ == "__main__":
    test_results = hybrid_search_with_metadata("What is climate finance?")
    for res in test_results:
        print(f"\nScore: {res['rerank_score']:.2f}")
        print(f"Source: {res['source_url']}")
        print(f"Text: {res['chunk_text'][:100]}...")
