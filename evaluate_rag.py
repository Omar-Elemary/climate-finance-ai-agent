import os
# Import our centralized retrieval engine
from retriever import hybrid_search_with_metadata

# 1. Define Ground-Truth Test Suite (5 queries as required by Week 1)
test_suite = [
    {
        "id": 1,
        "query": "What are the financial risks of climate debt?",
        "expected_topics": ["debt", "financial", "risks", "economies"]
    },
    {
        "id": 2,
        "query": "How much climate finance is required for adaptation?",
        "expected_topics": ["finance", "adaptation", "costs"]
    },
    {
        "id": 3,
        "query": "What physical climate risks impact global infrastructure?",
        "expected_topics": ["physical", "infrastructure", "threaten", "risks"]
    },
    {
        "id": 4,
        "query": "How do debt burdens affect lower-income nations?",
        "expected_topics": ["debt", "lower-income", "economies", "harm"]
    },
    {
        "id": 5,
        "query": "What funding mechanisms support climate resilience?",
        "expected_topics": ["finance", "adaptation", "climate", "mechanisms"]
    }
]

print("\nRunning RAG Retrieval Evaluation (Hybrid + Re-ranker) across 5 test queries...\n")

results = []
total_precision = 0.0
total_recall = 0.0

for test_case in test_suite:
    query = test_case["query"]
    expected_topics = test_case["expected_topics"]
    
    # 2. Retrieve top 3 records using our modular retriever
    retrieved_records = hybrid_search_with_metadata(query, final_k=3)
    retrieved_chunks = [record["chunk_text"] for record in retrieved_records]
    
    # 3. Precision@3: Fraction of retrieved chunks containing at least one expected topic
    relevant_chunks_count = 0
    for chunk in retrieved_chunks:
        chunk_lower = chunk.lower()
        if any(topic.lower() in chunk_lower for topic in expected_topics):
            relevant_chunks_count += 1
            
    precision_at_3 = relevant_chunks_count / len(retrieved_chunks) if retrieved_chunks else 0.0
    
    # 4. Topic Recall: Fraction of expected topics present across all top 3 chunks combined
    combined_text = " ".join(retrieved_chunks).lower()
    found_topics_count = sum(1 for topic in expected_topics if topic.lower() in combined_text)
    topic_recall = found_topics_count / len(expected_topics) if expected_topics else 0.0
    
    total_precision += precision_at_3
    total_recall += topic_recall
    
    results.append({
        "id": test_case["id"],
        "query": query,
        "precision": precision_at_3,
        "recall": topic_recall
    })
    
    print(f"Query {test_case['id']}: Precision@3 = {precision_at_3:.2f} | Topic Recall = {topic_recall:.2f}")

avg_precision = total_precision / len(test_suite)
avg_recall = total_recall / len(test_suite)

print(f"\nAverage Precision@3: {avg_precision:.2f}")
print(f"Average Topic Recall: {avg_recall:.2f}")

# 5. Save Quantitative Markdown Report
os.makedirs("docs", exist_ok=True)
report_path = os.path.join("docs", "evaluation.md")

with open(report_path, "w", encoding="utf-8") as f:
    f.write("# RAG Retrieval Evaluation Report\n\n")
    f.write("## Pipeline Architecture\n")
    f.write("- **Lexical Search:** BM25 (`rank_bm25`)\n")
    f.write("- **Dense Vector Search:** PostgreSQL `pgvector` (`all-MiniLM-L6-v2`)\n")
    f.write("- **Rank Fusion:** Reciprocal Rank Fusion (RRF, $k=60$)\n")
    f.write("- **Re-ranking:** Cross-Encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`)\n\n")
    f.write("## Quantitative Metrics\n\n")
    f.write("| ID | Test Query | Precision@3 | Topic Recall |\n")
    f.write("| :--- | :--- | :---: | :---: |\n")
    for r in results:
        f.write(f"| {r['id']} | {r['query']} | **{r['precision']:.2f}** | **{r['recall']:.2f}** |\n")
    f.write(f"| **Average** | *Overall System Benchmark* | **{avg_precision:.2f}** | **{avg_recall:.2f}** |\n\n")
    f.write("## Findings & Narrative\n")
    f.write("- Hybrid search combining dense and sparse retrieval ensures high keyword coverage and semantic matching.\n")
    f.write("- Cross-encoder re-ranking effectively prioritizes contextually relevant chunks before passing to the LLM.\n")

print(f"\nEvaluation complete! Report saved to {report_path}")