# RAG Retrieval Evaluation Report

## Pipeline Architecture
- **Lexical Search:** BM25 (`rank_bm25`)
- **Dense Vector Search:** PostgreSQL `pgvector` (`all-MiniLM-L6-v2`)
- **Rank Fusion:** Reciprocal Rank Fusion (RRF, $k=60$)
- **Re-ranking:** Cross-Encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`)

## Quantitative Metrics

| ID | Test Query | Precision@3 | Topic Recall |
| :--- | :--- | :---: | :---: |
| 1 | What are the financial risks of climate debt? | **1.00** | **0.75** |
| 2 | How much climate finance is required for adaptation? | **1.00** | **0.67** |
| 3 | What physical climate risks impact global infrastructure? | **1.00** | **0.75** |
| 4 | How do debt burdens affect lower-income nations? | **1.00** | **0.75** |
| 5 | What funding mechanisms support climate resilience? | **1.00** | **1.00** |
| **Average** | *Overall System Benchmark* | **1.00** | **0.78** |

## Findings & Narrative
- Hybrid search combining dense and sparse retrieval ensures high keyword coverage and semantic matching.
- Cross-encoder re-ranking effectively prioritizes contextually relevant chunks before passing to the LLM.
