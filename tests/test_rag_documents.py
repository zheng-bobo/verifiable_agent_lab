from pathlib import Path

from verifiable_agent_lab.rag.chunking import ChunkerConfig, chunk_documents
from verifiable_agent_lab.rag.documents import load_markdown_documents


def test_loader_keeps_bilingual_source_metadata(tmp_path: Path) -> None:
    (tmp_path / "note.md").write_text("# Note\n\nEnglish body.", encoding="utf-8")
    (tmp_path / "note.zh-CN.md").write_text("# 笔记\n\n中文内容。", encoding="utf-8")

    documents = load_markdown_documents(tmp_path)

    assert [document.source for document in documents] == ["note.md", "note.zh-CN.md"]
    assert [document.language for document in documents] == ["en", "zh-CN"]
    assert [document.title for document in documents] == ["Note", "笔记"]


def test_heading_aware_chunker_is_stable_and_bounded(tmp_path: Path) -> None:
    body = " ".join(f"token-{index}" for index in range(180))
    (tmp_path / "note.md").write_text(
        f"# Root\n\n## Retrieval\n\n{body}\n\n## Evaluation\n\nShort section.",
        encoding="utf-8",
    )
    documents = load_markdown_documents(tmp_path)
    config = ChunkerConfig(max_chars=300, overlap_chars=40)

    first = chunk_documents(documents, config)
    second = chunk_documents(documents, config)

    assert len(first) > 2
    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
    assert all(len(chunk.text) <= config.max_chars for chunk in first)
    assert any("Root > Retrieval" in chunk.heading for chunk in first)
    assert next(chunk for chunk in first if "Root > Retrieval" in chunk.heading).start_line == 5
    assert all(chunk.start_line <= chunk.end_line for chunk in first)
