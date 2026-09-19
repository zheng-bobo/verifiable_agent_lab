"""Heading-aware Markdown chunking with stable citation identifiers."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from verifiable_agent_lab.rag.types import Chunk, Document

_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class ChunkerConfig:
    """Character-based chunk limits suitable for bilingual Markdown."""

    max_chars: int = 1200
    overlap_chars: int = 160

    def __post_init__(self) -> None:
        if self.max_chars < 200:
            raise ValueError("max_chars must be at least 200")
        if not 0 <= self.overlap_chars < self.max_chars // 2:
            raise ValueError("overlap_chars must be non-negative and less than max_chars / 2")


@dataclass(frozen=True)
class _Section:
    heading: str
    body: str
    start_line: int


def chunk_documents(
    documents: list[Document], config: ChunkerConfig | None = None
) -> list[Chunk]:
    """Split all documents into stable heading-aware chunks."""

    resolved_config = config or ChunkerConfig()
    return [
        chunk
        for document in documents
        for chunk in chunk_document(document, resolved_config)
    ]


def chunk_document(document: Document, config: ChunkerConfig | None = None) -> list[Chunk]:
    """Split one document while retaining heading and line provenance."""

    resolved_config = config or ChunkerConfig()
    chunks: list[Chunk] = []
    for section in _sections(document):
        heading_prefix = section.heading[: max(0, resolved_config.max_chars // 3)]
        separator = "\n\n" if heading_prefix else ""
        body_limit = resolved_config.max_chars - len(heading_prefix) - len(separator)
        body_limit = max(body_limit, resolved_config.max_chars // 2)
        for piece, start_offset, end_offset in _split_text(
            section.body, body_limit, resolved_config.overlap_chars
        ):
            text = f"{heading_prefix}{separator}{piece}".strip()
            start_line = section.start_line + section.body[:start_offset].count("\n")
            end_line = section.start_line + section.body[:end_offset].count("\n")
            digest_input = f"{document.source}:{start_line}:{end_line}:{text}".encode()
            chunk_id = hashlib.sha256(digest_input).hexdigest()[:16]
            chunks.append(
                Chunk(
                    id=chunk_id,
                    document_id=document.id,
                    source=document.source,
                    language=document.language,
                    heading=section.heading,
                    text=text,
                    start_line=start_line,
                    end_line=max(start_line, end_line),
                )
            )
    return chunks


def _sections(document: Document) -> list[_Section]:
    lines = document.text.splitlines()
    heading_stack: list[str] = []
    sections: list[_Section] = []
    body_lines: list[str] = []
    body_start = 1

    def flush() -> None:
        nonlocal body_lines
        body = "\n".join(body_lines).strip()
        if body:
            sections.append(
                _Section(
                    heading=" > ".join(heading_stack) or document.title,
                    body=body,
                    start_line=body_start,
                )
            )
        body_lines = []

    for line_number, line in enumerate(lines, start=1):
        match = _HEADING_PATTERN.match(line)
        if match:
            flush()
            level = len(match.group(1))
            heading_stack[level - 1 :] = [match.group(2).strip()]
            body_start = line_number + 1
            continue
        if not body_lines and not line.strip():
            continue
        if not body_lines:
            body_start = line_number
        body_lines.append(line)
    flush()
    return sections


def _split_text(text: str, limit: int, overlap: int) -> list[tuple[str, int, int]]:
    if len(text) <= limit:
        return [(text, 0, len(text))]

    pieces: list[tuple[str, int, int]] = []
    start = 0
    while start < len(text):
        target = min(start + limit, len(text))
        end = target
        if target < len(text):
            search_from = start + max(limit // 2, 1)
            candidates = [
                text.rfind("\n\n", search_from, target),
                text.rfind("\n", search_from, target),
                text.rfind(" ", search_from, target),
            ]
            boundary = max(candidates)
            if boundary > start:
                end = boundary
        piece = text[start:end].strip()
        if piece:
            leading = len(text[start:end]) - len(text[start:end].lstrip())
            trailing = len(text[start:end].rstrip())
            pieces.append((piece, start + leading, start + trailing))
        if end >= len(text):
            break
        next_start = max(end - overlap, start + 1)
        while next_start < end and not text[next_start].isspace():
            next_start += 1
        start = min(next_start + 1, end)
    return pieces
