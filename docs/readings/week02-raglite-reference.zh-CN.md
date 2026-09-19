# 第二周参考笔记：RAGLite 与最小 RAG 基线

[English](week02-raglite-reference.md) | [简体中文](week02-raglite-reference.zh-CN.md)

## 为什么选择 RAGLite

[RAGLite](https://github.com/superlinear-ai/raglite) 是一个开源 RAG toolkit。它不依赖
LangChain，并把文档插入、向量或混合搜索、context retrieval、prompt 构造与生成暴露为可单独
调用的步骤。因此，它适合用来理解 RAG 的真实数据流，而不是把整个系统隐藏在一次 Agent 调用
后面。

本实验把 RAGLite 当作**架构参照，而不是运行时依赖**。第二周的目标是亲自实现并测量最小组件。
这样也避开了当前 RAGLite 版本的 NumPy 约束与本项目 NumPy 2 基线之间的依赖冲突。

## 组件映射

| 关注点 | RAGLite | 本实验 |
|---|---|---|
| 文档处理 | Markdown/PDF 处理与数据库写入 | 仓库 Markdown loader |
| Chunking | 语义切分、上下文化标题与 late chunking | 带 overlap 的 heading-aware 字符切分 |
| Embedding | 可配置的本地或托管 embedder | Ollama `qwen3-embedding:0.6b` |
| 存储 | 支持向量的 DuckDB 或 PostgreSQL | 内存 NumPy 矩阵与可移植 `.npz` cache |
| Retrieval | 向量、关键词、混合搜索与可选 reranking | 精确 cosine Top-K 搜索 |
| Context | 包含相邻 chunk 的 chunk span | 带来源路径与行号、可以引用的 chunk |
| Generation | LiteLLM 或本地 llama.cpp 模型 | 通过 HTTP 调用 Ollama `qwen3:4b` 并关闭 thinking |
| Structured output | 取决于 provider | 生成端 JSON Schema 加本地严格校验 |
| Evaluation | 可选 Ragas 集成与 benchmark | 确定性 grader 与 repeated-sampling 指标 |

RAGLite 的 programmable flow 可以概括为：

```text
insert_documents -> vector_search -> retrieve_context -> add_context -> rag
```

第二周实现保留同样的职责分离：

```text
load -> chunk -> embed/index -> retrieve Top-K -> grounded prompt -> sample -> validate -> evaluate
```

## 有意保留的基线限制

当前实现有意不加入 vector database、hybrid search、reranking、semantic chunking、相邻 chunk
扩展和 adaptive retrieval。对于目前十篇笔记组成的小语料，精确 cosine search 已经足够，而且每个
分数都可以直接检查。这些省略项构成后续清晰的升级路线：一次只加入一个变量，再与保存的基线比较
retrieval recall、最终正确率、延迟和成本。

## 使用的开源接口

- [RAGLite 源码与 programmable RAG 示例](https://github.com/superlinear-ai/raglite)
- [Ollama embedding API](https://docs.ollama.com/capabilities/embeddings)
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [用于多语言检索的 Qwen3 Embedding](https://ollama.com/library/qwen3-embedding)
