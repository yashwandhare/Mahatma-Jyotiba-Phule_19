# RAGex — Requirements & Planning Document

**Problem Statement:** PS-19 — Context-Aware Document QA with Dynamic RAG

---

## Purpose

This document defines what RAGex is and how it works.  
If a feature is not written here, it does not exist.

---

## 1. Problem Statement

Most AI document assistants hallucinate. They answer confidently even when documents do not contain the information.

**This project solves that by:**
- Answering ONLY from indexed documents
- Refusing when information is missing
- Providing exact source citations
- Using dynamic retrieval (not fixed top-K)

Judges test **judgment**, not just generation.

---

## 2. What RAGex Is

**RAGex** is a folder-based document question answering system that:
- Indexes local files (PDFs, text, code)
- Answers questions strictly from those files
- Cites sources (filename + page/line)
- Refuses when answers are not found

**Core principle:**  
*"A system that refuses correctly is smarter than one that answers confidently."*

---

## 3. Architecture

```
Folder → Parse → Chunk → Embed → Store (Offline Indexing)
                    ↓
Query → Embed → Retrieve (Dynamic) → Generate → Cite or Refuse
```

### Tech Stack
- **Language:** Python
- **Vector Store:** ChromaDB (local)
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2)
- **LLM:** Groq API (llama-3.3-70b-versatile)
- **Parsers:** pypdf, native Python file readers

---

## 4. Core Requirements

### 4.1 Folder Indexing
- Recursively scan folder
- Extract text from: `.pdf`, `.txt`, `.md`, `.py`, `.js`, `.java`, etc.
- Split into chunks with metadata
- Store embeddings locally

### 4.2 Chunk Metadata
Each chunk must store:
- `filename` (relative path)
- `file_type` (pdf/text/code)
- `page` (for PDFs) OR `line_start`, `line_end` (for text/code)
- `chunk_id` (unique hash)

### 4.3 Dynamic Retrieval (MANDATORY)
**Not fixed top-K.**

Implementation uses:
1. **Similarity threshold:** Minimum score = 0.40
2. **Drop-off detection:** Stop when score drops > 0.10

This ensures:
- High-relevance questions get many chunks
- Low-relevance questions get few or zero chunks
- Irrelevant questions trigger refusal

### 4.4 Refusal Logic (CRITICAL)
When documents do NOT contain the answer, system responds with **EXACTLY:**

```
Answer: Not found in indexed documents.
```

**No partial answers. No speculation. No guessing.**

### 4.5 Source Citations
Every answer must list sources:
- Format: `filename (page N)` or `filename (lines X-Y)`
- All used sources must be listed
- Deterministic extraction (no LLM hallucination)

---

## 5. RAG Pipeline

```
User Query
  → Embed query
  → Fetch top 20 candidates (wide net)
  → Filter by similarity threshold (≥ 0.40)
  → Apply drop-off detection (variable K)
  → If chunks exist: Generate grounded answer + citations
  → If no chunks: Return refusal
```

**LLM Grounding:**
- System prompt enforces context-only answers
- Low temperature (0.1) for determinism
- Post-generation check for refusal formatting

---

## 6. Supported File Types

| Type | Extensions | Source Format |
|------|-----------|---------------|
| PDF | `.pdf` | page number |
| Text | `.txt`, `.md` | line range |
| Code | `.py`, `.js`, `.java`, `.ts`, `.cpp`, `.c`, `.h`, `.html`, `.css`, `.json`, `.yaml`, `.sh` | line range |

Files are split into 50-line segments for traceability.

---

## 7. What We DO NOT Build

- ❌ Cloud-only solutions
- ❌ Authentication or user management
- ❌ Dashboards or admin panels
- ❌ Multimodal input (images, audio)
- ❌ Model training or fine-tuning
- ❌ Web crawling

---

## 8. Quality Expectations

The system must be:
- **Deterministic:** Same query = same answer
- **Explainable:** Every answer traced to source
- **Demo-safe:** No crashes, clear outputs
- **Hallucination-resistant:** Refusal over guessing

**Success Criteria:**
- Grounded answers with correct citations
- Explicit refusal on missing information
- Fully functional pipeline (index → query → answer/refuse)

---

## 9. Demo Flow

**The winning moment:**

1. **Valid question** → Answer with citations  
   Example: "What is a microprocessor?" → Answer + source

2. **Invalid question** → Exact refusal  
   Example: "What is the capital of Mars?" → `"Answer: Not found in indexed documents."`

This contrast proves trust and prevents hallucination.

---

## 10. System Behavior Examples

### Example 1: Valid Query
```
Query: "What is a microprocessor?"
Retrieved: 3 chunks (scores: 0.85, 0.78, 0.65)
Answer: "A microprocessor is a central processing unit..."
Sources:
- computer_basics.pdf (page 12)
- hardware_guide.txt (lines 45-95)
```

### Example 2: Invalid Query
```
Query: "What is the capital of Mars?"
Retrieved: 0 chunks (top score: 0.22, below threshold)
Answer: Not found in indexed documents.
Sources: []
```

### Example 3: Drop-off Detection
```
Query: "Python syntax"
Candidates: 20 chunks fetched
After threshold: 8 chunks (scores: 0.81, 0.79, 0.76, 0.71, 0.68, 0.50, 0.49, 0.47)
After drop-off: 5 chunks (stopped at 0.68 → 0.50, drop = 0.18)
```

---

## 11. Why RAGex Is Unique

**Most teams:**
- Use fixed top-K (always retrieve same amount)
- Always answer something (even wrong)
- Weak source traceability

**RAGex:**
- Adaptive retrieval (threshold + drop-off)
- Mandatory refusal (trust > confidence)
- Exact source citations (file + page/line)
- Fully offline-capable (except LLM API)

This demonstrates **engineering maturity**, not just ML usage.

---

## 12. Implementation Notes

### File Structure
```
backend/app/rag/
  ├── loader.py      # File parsing with metadata
  ├── chunker.py     # Overlapping chunks
  ├── store.py       # ChromaDB + embeddings
  ├── retriever.py   # Dynamic threshold retrieval
  └── generator.py   # Groq-based grounded generation
```

### Key Parameters
- Chunk size: 2000 chars (~500 tokens)
- Chunk overlap: 200 chars
- Candidate K: 20
- Min similarity: 0.40
- Drop-off threshold: 0.10
- LLM temperature: 0.1

---

## 13. Testing Checklist

- [x] PDF parsing with page numbers
- [x] Text/code parsing with line ranges
- [x] Chunking preserves metadata
- [x] Embeddings stored in ChromaDB
- [x] Threshold filtering works
- [x] Drop-off detection reduces K
- [x] Refusal triggers on low scores
- [x] Sources extracted correctly
- [x] LLM generates grounded answers
- [x] Exact refusal format enforced

---

## 14. Timeline & Constraints

- **Coding window:** 1:00 PM – 4:30 PM
- **Commit frequency:** Every 30 minutes
- **Demo preparation:** Final 30 minutes

---

## 15. Final Philosophy

**Correct refusal is a success, not a failure.**

The system's value comes from knowing when it doesn't know, not from always having an answer.

This is what makes RAGex trustworthy.
