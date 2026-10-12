# Retrieval Architecture Guide

ATLAS uses SQLite FTS5 for keyword-based retrieval of local text documents. Uploaded content is normalized, chunked with overlap, indexed, and ranked by BM25. Each result includes a stable citation identifier in the format doc:N#chunk:M.

For larger or more semantic corpora, a future extension can introduce embeddings, hybrid lexical-vector retrieval, reranking, per-tenant document access control, and evaluation using a held-out question set.

BM25 and overlapping chunks are practical baselines, not a guarantee of semantic relevance. A retrieval hit does not prove an answer is correct, and merely printing a citation does not prove it supports the claim.

The demo provider performs deterministic tool routing and displays snippets. Live model providers synthesize their own responses, ideally with citations grounded in tool results.
