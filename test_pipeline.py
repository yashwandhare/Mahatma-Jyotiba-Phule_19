"""End-to-end sanity test for RAGex. Run from project root: python test_pipeline.py"""

from backend.app.rag.loader import load_files
from backend.app.rag.chunker import Chunker
from backend.app.rag.store import index_chunks, clear_index
from backend.app.rag.retriever import retrieve
from backend.app.rag.generator import generate_answer

DOCS_PATH = "docs/demo"


def main():
    print("=== RAGex Sanity Test ===")

    print("[1] Clearing vector database...")
    clear_index()

    print("[2] Loading documents...")
    docs = load_files(DOCS_PATH)
    print(f"Loaded documents: {len(docs)}")

    if not docs:
        print("❌ No documents loaded. Check DOCS_PATH.")
        return

    print("[3] Chunking documents...")
    chunks = Chunker().chunk(docs)
    print(f"Generated chunks: {len(chunks)}")

    if not chunks:
        print("❌ No chunks generated.")
        return

    print("[4] Indexing chunks...")
    index_chunks(chunks)
    print("Indexing complete.")

    print("[5] Testing VALID query...")
    valid_query = "what is a microprocessor?"
    retrieved = retrieve(valid_query)
    print(f"Retrieved chunks: {len(retrieved['chunks'])}")

    result = generate_answer(valid_query, retrieved["chunks"])
    print("Answer:")
    print(result["answer"])
    print("Sources:")
    for s in result["sources"]:
        print("-", s)

    print("\n[6] Testing INVALID query...")
    invalid_query = "what is the capital of mars"
    retrieved = retrieve(invalid_query)
    result = generate_answer(invalid_query, retrieved["chunks"])

    print("Answer:")
    print(result["answer"])
    print("Sources:", result["sources"])

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
