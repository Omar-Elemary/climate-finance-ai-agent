import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. Import your powerful hybrid search module
from retriever import hybrid_search_with_metadata

# 2. Securely load the API Key from the hidden .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found. Please add it to your .env file.")

client = genai.Client(api_key=api_key)

def format_context_block(records: list) -> tuple[str, list]:
    """Formats retrieved chunks with their source URLs for prompt injection."""
    context_parts = []
    sources = []
    
    for i, r in enumerate(records, 1):
        url = r.get("source_url", "Unknown Source")
        text = r.get("chunk_text", "")
        sources.append(url)
        context_parts.append(f"[Context {i}] (Source: {url}):\n{text}\n")
        
    return "\n".join(context_parts), sources

def run_agent(user_question: str):
    print(f"\n1. Running Hybrid Retrieval (BM25 + pgvector + RRF + Cross-Encoder)...")
    
    # 3. Execute the advanced hybrid search
    retrieved_records = hybrid_search_with_metadata(user_question, final_k=3)
    
    if not retrieved_records:
        print("No relevant context found in database.")
        return

    # Extract the text and source URLs
    context_text, sources = format_context_block(retrieved_records)

    prompt = f"""You are a professional climate finance research analyst.
Answer the user's question using ONLY the provided verified context below.
If the context does not contain enough information, explicitly state that you do not have sufficient data in the database. Do not hallucinate or make assumptions.
Cite the relevant Context numbers when stating facts.

---
PROVIDED CONTEXT:
{context_text}
---

USER QUESTION: {user_question}
"""

    print("2. Sending grounded context to Gemini for synthesis...")
    response = client.models.generate_content(
        model='gemini-3.5-flash',  # Fast, highly accurate production flash model
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2  # Low temperature forces the AI to stick strictly to the facts
        )
    )

    print("\n" + "=" * 60)
    print("FINAL AGENT RESPONSE:")
    print("=" * 60)
    print(response.text.strip())
    print("\n" + "-" * 60)
    print("VERIFIED SOURCES & CITATIONS:")
    print("-" * 60)
    
    # Remove duplicate URLs and print them neatly
    for src in list(dict.fromkeys(sources)):
        print(f"- {src}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    print("Climate Finance AI Agent Ready. (Type 'exit' to quit)")
    while True:
        query = input("\nEnter your question: ").strip()
        if query.lower() in ["exit", "quit", "q"]:
            break
        if query:
            run_agent(query)