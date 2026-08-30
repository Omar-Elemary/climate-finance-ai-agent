import pickle
import string
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer, CrossEncoder

print("Initializing Hybrid Retriever Models & Indexes...")

# 1. Load AI Models
embedder = SentenceTransformer('all-MiniLM-L6-v2')
cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

# 2. Load Lexical Index (BM25)
try:
    with open("bm25_index.pkl", "rb") as f:
        bm25_data = pickle.load(f)
        bm25_model = bm25_data["bm25_index"]
        bm25_ids = bm25_data["chunk_ids"]
except FileNotFoundError:
    print("Warning: bm25_index.pkl not found. Make sure you run embedder.py first.")
    bm25_model, bm25_ids = None, []

# 3. Database Connection
try:
    conn = psycopg2.connect(
        host="localhost", 
        port=5432, 
        database="climate_db", 
        user="postgres", 
        password="postgres"
    )
    register_vector(conn)
    cursor = conn.cursor()
except Exception as e:
    print(f"Database connection failed: {e}")

def tokenize(text: str) -> list:
    """Helper function to clean text for BM25 matching."""
    text = text.lower()
    return text.translate(str.maketrans('', '', string.punctuation)).split()

def get_chunk_data(id_list: list) -> dict:
    """Fetches text and source URLs from PostgreSQL."""
    if not id_list:
        return {}
    format_strings = ','.join(['%s'] * len(id_list))
    cursor.execute(f"""
        SELECT id, source_url, chunk_text 
        FROM climate_docs 
        WHERE id IN ({format_strings})
    """, tuple(id_list))
    
    return {row[0]: {"source_url": row[1], "chunk_text": row[2]} for row in cursor.fetchall()}

def hybrid_search_with_metadata(query: str, top_k=30, rrf_k=60, final_k=3) -> list:
    """Executes Dual Search, RRF Merge, and Cross-Encoder Re-ranking."""
    
    # --- STAGE 1: DUAL RETRIEVAL ---
    # A. BM25 Lexical
    tokenized_query = tokenize(query)
    bm25_scores = bm25_model.get_scores(tokenized_query) if bm25_model else []
    bm25_results = [item[0] for item in sorted(zip(bm25_ids, bm25_scores), key=lambda x: x[1], reverse=True)[:top_k]]

    # B. Vector Semantic
    query_vector = embedder.encode(query).tolist()
    cursor.execute("""
        SELECT id FROM climate_docs 
        ORDER BY embedding <=> %s::vector LIMIT %s;
    """, (query_vector, top_k))
    vector_results = [row[0] for row in cursor.fetchall()]

    # --- STAGE 2: RECIPROCAL RANK FUSION (RRF) ---
    rrf_scores = {}
    for rank, chunk_id in enumerate(bm25_results):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (rrf_k + rank + 1)
    for rank, chunk_id in enumerate(vector_results):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (rrf_k + rank + 1)

    # Sort merged results and slice top 20 candidates
    candidate_ids = [item[0] for item in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:20]]

    # --- STAGE 3: HYDRATION ---
    chunk_data_map = get_chunk_data(candidate_ids)
    
    # --- STAGE 4: CROSS-ENCODER RE-RANKING ---
    cross_input = [[query, chunk_data_map[cid]["chunk_text"]] for cid in candidate_ids]
    rerank_scores = cross_encoder.predict(cross_input)
    
    # Sort by the final neural score
    reranked_results = sorted(zip(candidate_ids, rerank_scores), key=lambda x: x[1], reverse=True)[:final_k]
    
    # Format and return the final records
    final_records = []
    for cid, score in reranked_results:
        final_records.append({
            "id": cid,
            "source_url": chunk_data_map[cid]["source_url"],
            "chunk_text": chunk_data_map[cid]["chunk_text"],
            "rerank_score": float(score)
        })
        
    return final_records

if __name__ == "__main__":
    # Test block to verify it works standalone
    test_results = hybrid_search_with_metadata("What is climate finance?")
    for res in test_results:
        print(f"\nScore: {res['rerank_score']:.2f}")
        print(f"Source: {res['source_url']}")
        print(f"Text: {res['chunk_text'][:100]}...")