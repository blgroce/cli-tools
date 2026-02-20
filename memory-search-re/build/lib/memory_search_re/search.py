"""Hybrid search with Reciprocal Rank Fusion."""

from .config import (
    DEFAULT_MAX_RESULTS,
    DEFAULT_MIN_SCORE,
    VECTOR_WEIGHT,
    BM25_WEIGHT,
    RRF_K,
)
from .db import MemoryDB
from .embeddings import embed_query


def hybrid_search(
    db: MemoryDB,
    query: str,
    limit: int = DEFAULT_MAX_RESULTS,
    min_score: float = DEFAULT_MIN_SCORE,
) -> list[dict]:
    """Hybrid vector + BM25 search with Reciprocal Rank Fusion.

    Returns list of {chunk_id, file_path, start_line, end_line, content, score}.
    """
    # Get more candidates than needed for better fusion
    candidate_limit = limit * 4

    # Vector search
    query_embedding = embed_query(query)
    vec_results = db.vector_search(query_embedding, candidate_limit)

    # BM25 search — FTS5 query syntax: quote terms for phrase-like matching
    # Split query into words for OR matching
    fts_query = " OR ".join(
        f'"{w}"' for w in query.split() if len(w) > 1
    )
    bm25_results = []
    if fts_query:
        try:
            bm25_results = db.bm25_search(fts_query, candidate_limit)
        except Exception:
            # FTS query can fail on special characters — graceful fallback
            pass

    # Build RRF scores
    # Vector: lower distance = better, so rank 0 = closest
    vec_scores = {}
    for rank, r in enumerate(vec_results):
        vec_scores[r["chunk_id"]] = 1.0 / (rank + RRF_K)

    # BM25: already sorted by rank (lower = better match)
    bm25_scores = {}
    for rank, r in enumerate(bm25_results):
        bm25_scores[r["chunk_id"]] = 1.0 / (rank + RRF_K)

    # Merge
    all_chunk_ids = set(vec_scores.keys()) | set(bm25_scores.keys())
    scored = []
    for chunk_id in all_chunk_ids:
        v = vec_scores.get(chunk_id, 0)
        b = bm25_scores.get(chunk_id, 0)
        score = VECTOR_WEIGHT * v + BM25_WEIGHT * b
        scored.append((chunk_id, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    # Filter by min score and limit
    top = [(cid, s) for cid, s in scored if s >= min_score][:limit]

    if not top:
        return []

    # Fetch chunk details
    chunk_ids = [cid for cid, _ in top]
    chunks = db.get_chunks_by_ids(chunk_ids)
    score_map = dict(top)

    results = []
    for chunk_id in chunk_ids:
        chunk = chunks.get(chunk_id)
        if not chunk:
            continue
        # Truncate content for snippet
        content = chunk["content"]
        snippet = content[:700] + "..." if len(content) > 700 else content
        results.append({
            "chunk_id": chunk_id,
            "file_path": chunk["file_path"],
            "start_line": chunk["start_line"],
            "end_line": chunk["end_line"],
            "snippet": snippet,
            "score": round(score_map[chunk_id], 4),
        })

    return results
