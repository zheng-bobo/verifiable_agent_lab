"""Markdown document loading for the small bilingual knowledge base."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from verifiable_agent_lab.rag.types import Document

_TITLE_PATTERN = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def load_markdown_documents(root: Path) -> list[Document]:
    """Load Markdown files below ``root`` in deterministic path order.

    The repository path is stored relative to ``root`` so citations remain
    portable across machines. Chinese translations are identified by the
    ``.zh-CN.md`` filename suffix.
    """

    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"knowledge-base directory does not exist: {root}")

    documents: list[Document] = []
    for path in sorted(root.rglob("*.md")):
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
        if not text:
            continue
        source = path.relative_to(root).as_posix()
        title_match = _TITLE_PATTERN.search(text)
        title = title_match.group(1).strip() if title_match else path.stem
        language = "zh-CN" if path.name.endswith(".zh-CN.md") else "en"
        document_id = hashlib.sha256(source.encode()).hexdigest()[:16]
        documents.append(
            Document(
                id=document_id,
                source=source,
                language=language,
                title=title,
                text=text,
            )
        )
    if not documents:
        raise ValueError(f"no Markdown documents found below: {root}")
    return documents
