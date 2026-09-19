# Week 2 Reference Note: RAGLite and the Minimal RAG Baseline

[English](week02-raglite-reference.md) | [简体中文](week02-raglite-reference.zh-CN.md)

## Why RAGLite

[RAGLite](https://github.com/superlinear-ai/raglite) is an open-source RAG toolkit that exposes a
programmable retrieval path without depending on LangChain. Its public API separates document
insertion, vector or hybrid search, context retrieval, prompt construction, and generation. This
makes it a useful reference for learning the data flow rather than hiding the whole system behind a
single agent call.

The lab uses RAGLite as an **architecture reference, not a runtime dependency**. The goal of Week 2
is to implement and measure the baseline components directly. This also avoids a dependency conflict
between the current RAGLite release's NumPy constraint and this project's NumPy 2 baseline.

## Component Mapping

| Concern | RAGLite | This lab |
|---|---|---|
| Document processing | Markdown/PDF processing and database insertion | Repository Markdown loader |
| Chunking | Semantic splitting, contextual headings, and late chunking | Heading-aware character chunks with overlap |
| Embedding | Configurable local or hosted embedder | Ollama `qwen3-embedding:0.6b` |
| Storage | DuckDB or PostgreSQL with vector support | Portable in-memory NumPy matrix and `.npz` cache |
| Retrieval | Vector, keyword, hybrid search, and optional reranking | Exact cosine Top-K search |
| Context | Chunk spans with neighboring chunks | Citable chunks with source paths and line numbers |
| Generation | LiteLLM or local llama.cpp models | Ollama `qwen3:4b` over HTTP with thinking disabled |
| Structured output | Provider-dependent | JSON Schema at generation plus strict local validation |
| Evaluation | Optional Ragas integration and benchmarks | Deterministic graders and repeated-sampling metrics |

RAGLite's programmable flow is approximately:

```text
insert_documents -> vector_search -> retrieve_context -> add_context -> rag
```

The Week 2 implementation keeps the same separation:

```text
load -> chunk -> embed/index -> retrieve Top-K -> grounded prompt -> sample -> validate -> evaluate
```

## Deliberate Baseline Limits

This implementation intentionally omits a vector database, hybrid search, reranking, semantic
chunking, neighboring-span expansion, and adaptive retrieval. Exact cosine search is sufficient for
the current ten-note corpus and makes every score inspectable. These omitted features now form a
clear upgrade path: add one at a time and measure retrieval recall, final accuracy, latency, and cost
against the saved baseline.

## Supporting Open-Source Interfaces

- [RAGLite source and programmable RAG example](https://github.com/superlinear-ai/raglite)
- [Ollama embedding API](https://docs.ollama.com/capabilities/embeddings)
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [Qwen3 Embedding model for multilingual retrieval](https://ollama.com/library/qwen3-embedding)
