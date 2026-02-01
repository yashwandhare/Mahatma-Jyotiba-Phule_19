"""Canonical indexing pipeline shared by CLI and API."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import logging

from backend.app.rag import loader, chunker, store

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IndexingResult:
    """Stable contract for indexing outcomes."""

    documents_indexed: int
    chunks_indexed: int
    files_skipped: int
    index_cleared: bool
    chunks_removed: int
    final_index_size: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def index_paths(paths: List[str], clear_index: bool = False) -> IndexingResult:
    """
    Validate, load, chunk, and index documents end-to-end.
    
    INVARIANT: Single indexing pipeline for all callers (INVARIANTS.md §7).
    CLI, API, and all entry points must use this function.
    """
    collection = store.ensure_collection_ready()
    initial_count = collection.count()

    index_cleared = bool(clear_index)
    chunks_removed = 0

    if clear_index:
        store.clear_index()
        chunks_removed = initial_count
        collection = store.ensure_collection_ready()

    docs, errors = loader.load_inputs(paths)
    files_skipped = len(errors)

    if not docs:
        final_size = store.ensure_collection_ready().count()
        logger.info(
            "No documents indexed (skipped=%s, cleared=%s)",
            files_skipped,
            index_cleared,
        )
        return IndexingResult(
            documents_indexed=0,
            chunks_indexed=0,
            files_skipped=files_skipped,
            index_cleared=index_cleared,
            chunks_removed=chunks_removed,
            final_index_size=final_size,
        )

    chunker_inst = chunker.Chunker()
    chunks = chunker_inst.chunk(docs)
    store.index_chunks(chunks)

    final_size = store.ensure_collection_ready().count()

    result = IndexingResult(
        documents_indexed=len(docs),
        chunks_indexed=len(chunks),
        files_skipped=files_skipped,
        index_cleared=index_cleared,
        chunks_removed=chunks_removed,
        final_index_size=final_size,
    )

    logger.info(
        "Indexed %s documents into %s chunks (skipped=%s, cleared=%s, collection=%s)",
        result.documents_indexed,
        result.chunks_indexed,
        result.files_skipped,
        result.index_cleared,
        result.final_index_size,
    )

    return result


def clean_index() -> int:
    """Remove all entries from the index, returning number of chunks removed."""
    collection = store.ensure_collection_ready()
    existing = collection.count()
    store.clear_index()
    logger.info("Index cleared (removed %s chunks)", existing)
    return existing
