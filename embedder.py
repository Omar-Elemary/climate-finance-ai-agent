import json
import pickle
import string
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

# 1. Initialize models and database connection
embedder = SentenceTransformer('all-MiniLM-L6-v2')

conn = psycopg2.connect(
    host="localhost", port=5434, database="climate_rag", 
    user="postgres", password="postgres"
)
cursor = conn.cursor()
register_vector(conn)

# Clear old rows to prevent duplicates during testing
cursor.execute("TRUNCATE TABLE climate_docs RESTART IDENTITY;")
conn.commit()

def tokenize(text):
    """Helper function to lowercase and remove punctuation for BM25."""
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text.split()

print("Reading real chunks from the chunker...")
with open("data/chunks/master_chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

chunk_ids = []
tokenized_corpus = []

print(f"Processing {len(chunks)} chunks for Vectors and BM25...")

# 2. Loop through the real JSON chunks to populate both pipelines
for doc in chunks:
    text = doc["text"]
    source_url = doc.get("source_url", "Unknown")
    doc_id = doc.get("parent_doc_id", "Unknown")
    
    # --- A. Vector Processing ---
    embedding = embedder.encode(text).tolist()
    
    # Insert text, vector, AND METADATA into PostgreSQL
    cursor.execute("""
        INSERT INTO climate_docs (doc_id, source_url, chunk_text, embedding) 
        VALUES (%s, %s, %s, %s) 
        RETURNING id;
    """, (doc_id, source_url, text, embedding))
    
    inserted_id = cursor.fetchone()[0]
    chunk_ids.append(inserted_id)
    
    # --- B. BM25 Tokenization ---
    tokenized_corpus.append(tokenize(text))

conn.commit()
cursor.close()
conn.close()

# 3. Build the BM25 Index
print("Building the BM25 Index...")
bm25 = BM25Okapi(tokenized_corpus)

# 4. Save the Index and the ID mapping to your local hard drive
print("Saving BM25 index to bm25_index.pkl...")
with open("bm25_index.pkl", "wb") as f:
    pickle.dump({
        "bm25_index": bm25,
        "chunk_ids": chunk_ids
    }, f)

print("Pipeline complete! Vectors and metadata saved to DB, BM25 saved to disk.")