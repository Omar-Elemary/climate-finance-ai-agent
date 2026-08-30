import psycopg2
from pgvector.psycopg2 import register_vector

def setup_db():
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="climate_db",
        user="postgres",
        password="postgres"
    )
    cursor = conn.cursor()

    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    register_vector(conn)

    print("Building schema with metadata columns...")
    cursor.execute("""
        DROP TABLE IF EXISTS climate_docs;
        CREATE TABLE climate_docs (
            id SERIAL PRIMARY KEY,
            doc_id VARCHAR(255),
            source_url TEXT,
            chunk_text TEXT,
            embedding vector(384)
        );
    """)

    conn.commit()
    cursor.close()
    conn.close()

    print("Success: PostgreSQL schema is ready for ingestion!")

if __name__ == "__main__":
    setup_db()