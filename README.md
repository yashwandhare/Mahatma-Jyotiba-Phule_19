# RAGex

**Context-Aware Document QA with Dynamic RAG**

RAGex answers questions strictly from your local documents—or refuses when information is missing.

---

## What It Does

- Indexes local folders (PDFs, text files, code)
- Retrieves relevant chunks dynamically (not fixed top-K)
- Generates grounded answers with source citations
- Refuses explicitly when documents lack the answer

---

## Quick Start

### 1. Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Configure
Create `.env` file:
```
GROQ_API_KEY=your_key_here
```

### 3. Test Pipeline
```bash
python test_pipeline.py
```

Expected output:
- Valid query → Answer + citations
- Invalid query → `"Answer: Not found in indexed documents."`

---

## Project Structure

```
backend/app/rag/    # Core RAG pipeline
  ├── loader.py     # File parsing
  ├── chunker.py    # Text chunking
  ├── store.py      # Vector storage
  ├── retriever.py  # Dynamic retrieval
  └── generator.py  # Answer generation

docs/               # Documentation + demo files
test_pipeline.py    # End-to-end test
```

---

## Key Features

**Dynamic Retrieval**
- Similarity threshold: 0.40
- Drop-off detection: 0.10
- Variable context size per query

**Source Citations**
- PDFs: filename + page number
- Text/Code: filename + line range

**Mandatory Refusal**
- No hallucination
- No speculation
- Exact format enforced

---

## Philosophy

*"A system that refuses correctly is smarter than one that answers confidently."*

See [docs/RPD.md](docs/RPD.md) for complete requirements and architecture.
