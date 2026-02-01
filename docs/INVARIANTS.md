# RAGex Core Invariants

This document defines the **non-negotiable system guarantees** that must never change. Violations of these invariants indicate critical bugs or architectural regressions.

## Purpose

RAGex is a **frozen-scope local-first RAG system**. These invariants exist to:
- Prevent silent regressions during maintenance
- Make it hard to accidentally break core guarantees
- Document what future changes **must preserve**

---

## 1. Indexing is Always Explicit

**Guarantee**: The vector index is only modified through explicit user commands.

**What this means**:
- Querying operations (`--ask`, `/ask`, REPL) **never** trigger indexing
- Index only changes via: `ragex <paths>`, `/index`, `/upload`, or `ragex clean`
- No automatic re-indexing, background updates, or silent mutations

**Enforcement**:
- `retriever.retrieve()` has no write access to store
- `generator.generate_answer()` only reads retrieved chunks
- `store.get_collection()` is read-only during queries

**Violation examples** (forbidden):
- "Smart" query-time document updates
- Automatic index refreshes
- Cache invalidation that triggers re-indexing

---

## 2. Queries Never Mutate the Index

**Guarantee**: All query operations are read-only with respect to the vector store.

**What this means**:
- Retrieval, generation, and listing operations cannot modify indexed documents
- Failed queries leave the index unchanged
- Query behavior is deterministic given the same index state

**Enforcement**:
- Query paths only call `collection.query()` and `collection.count()`
- No `collection.add()`, `collection.delete()`, or `collection.update()` in retrieval/generation
- `IndexStateError` raised if collection is missing—never auto-created during queries

**Violation examples** (forbidden):
- Query-time document augmentation
- Automatic index repair during retrieval
- Storing query feedback in the index

---

## 3. Offline Mode Forbids All Remote Network Calls

**Guarantee**: When `OFFLINE_MODE=1`, no network traffic leaves localhost.

**What this means**:
- Groq and all remote providers fail immediately with clear error
- Ollama only works if `OLLAMA_BASE_URL` points to localhost (127.0.0.1, ::1, or localhost)
- No external API calls, telemetry, or update checks

**Enforcement**:
- `LLMOrchestrator._ensure_offline_policy()` blocks non-Ollama providers
- Ollama URL validated to be local-only in offline mode
- Check happens before any client initialization or HTTP request

**Violation examples** (forbidden):
- Fallback to remote providers when Ollama fails
- Anonymous usage telemetry
- Checking for updates online

---

## 4. Providers Are Behaviorally Indistinguishable

**Guarantee**: Groq and Ollama exhibit identical behavior at system boundaries.

**What this means**:
- Same retry counts (2 retries, 3 total attempts)
- Same backoff timing (exponential: 2^attempt seconds)
- Same error types (`ProviderTimeout` vs `ProviderUnavailable`)
- Same canonical error messages (no provider-specific text)
- Same empty-response handling (both raise `ProviderUnavailable`)
- No provider names in generation logs

**Enforcement**:
- `LLMOrchestrator` Provider Interface Contract documented in code
- Both `_GroqProvider` and `_OllamaProvider` implement identical retry/error logic
- `get_error_message()` returns provider-agnostic strings
- Logging uses generic "LLM request" wording

**Violation examples** (forbidden):
- Conditional behavior based on active provider
- Different timeout handling for different backends
- Provider name in user-facing error messages

---

## 5. Refusal Response is Exact and Enforced

**Guarantee**: When the answer is not found, the system returns the exact configured refusal string.

**What this means**:
- Default: `"Answer: Not found in indexed documents."`
- Configurable via `REFUSAL_RESPONSE` in config
- No paraphrasing, no variations, no LLM creativity
- Enforced only for `QueryIntent.FACTUAL` queries

**Enforcement**:
- `generator.generate_answer()` normalizes LLM refusals to canonical string
- Empty chunk list triggers immediate refusal return (no LLM call)
- Config value validated to be non-empty string

**Violation examples** (forbidden):
- LLM-generated refusal variations ("I cannot find...", "The document doesn't mention...")
- Different refusal text for different intents (all must use canonical)
- Returning empty string or null instead of refusal

---

## 6. Single Configuration Source of Truth

**Guarantee**: All configuration flows through `backend.app.core.config` module.

**What this means**:
- Load order: defaults → .env → environment → CLI flags (via env vars)
- No direct `os.getenv()` or `os.environ[]` reads for RAGex settings in backend
- Every config value has explicit default and description
- Runtime validation for critical config (API keys, offline mode)

**Enforcement**:
- `config.py` is the only module that reads environment variables for RAGex settings
- All backend modules import from `config` singleton
- `validate_runtime_requirements()` called before LLM generation

**Violation examples** (forbidden):
- Reading `RAG_PROVIDER` directly from environment in orchestrator
- Hardcoded defaults outside config.py
- Bypassing config validation

---

## 7. Single Canonical Indexing Pipeline

**Guarantee**: All indexing flows through `indexer.index_paths()`.

**What this means**:
- CLI, `/index`, `/upload` all call the same function
- No duplicate validation/loading/chunking logic
- Returns canonical `IndexingResult` dataclass
- Clear-index handling is part of pipeline, never separate

**Enforcement**:
- `indexer.index_paths()` is the only public indexing API
- Deprecated helpers (`load_files`, `_load_folder`) removed
- `IndexingResult` is immutable and serialized verbatim

**Violation examples** (forbidden):
- Custom indexing logic in API routes
- CLI-specific ingestion shortcuts
- Direct calls to `store.index_chunks()` bypassing pipeline

---

## 8. Validation is Non-Fatal and Aggregated

**Guarantee**: Invalid files are skipped, never crash indexing.

**What this means**:
- `files.collect_valid_files()` is the single validation authority
- Unsupported extensions, oversized files, unreadable paths are logged and skipped
- Users see aggregated skip counts, not per-file errors
- At least one valid file must exist for indexing to succeed

**Enforcement**:
- `collect_valid_files()` returns `(valid_files, skipped_count)`
- Loader never raises exceptions for individual file failures
- Zero valid files after validation triggers clear error, not crash

**Violation examples** (forbidden):
- Fatal errors on invalid file extensions
- Per-file error UI (only aggregates allowed)
- Indexing proceeding with zero valid files

---

## 9. Vector Store Failures Are Explicit

**Guarantee**: Missing or corrupted vector store raises `IndexStateError` with recovery guidance.

**What this means**:
- No silent collection creation during queries
- No automatic index repair or reset
- Users must run `ragex clean` to fix corrupted store
- `ensure_collection_ready()` probes store before every operation

**Enforcement**:
- `store.IndexStateError` raised when collection cannot be accessed
- All index/query/list operations call `ensure_collection_ready()` first
- Error message includes explicit recovery command

**Violation examples** (forbidden):
- Auto-creating empty collection during query
- Silently resetting corrupted database
- Continuing with degraded store state

---

## 10. CLI and API Behave Identically

**Guarantee**: CLI and API endpoints follow identical logic and return consistent results.

**What this means**:
- Same validation rules (via `collect_valid_files()`)
- Same indexing pipeline (via `index_paths()`)
- Same error messages (via `get_error_message()`)
- Same configuration (via `config` singleton)

**Enforcement**:
- Shared backend modules for all operations
- No CLI-only or API-only code paths
- `IndexingResult` serialized identically for both

**Violation examples** (forbidden):
- Different skip behavior in CLI vs API
- API-specific error handling
- CLI shortcuts that bypass backend validation

---

## Scope Freeze

**What is in scope** (frozen):
- Document ingestion (PDF, TXT, MD, code files)
- Vector-based retrieval with semantic search
- LLM-based answer generation with RAG
- Intent detection (factual, summary, description)
- Offline mode support
- CLI and API interfaces
- Configuration management

**What is explicitly out of scope** (will never be added):
- Multi-user support or authentication
- Streaming responses
- Fine-tuning or model training
- Web scraping or URL ingestion
- Real-time document monitoring
- Cloud deployment automation
- Database migrations or versioning
- Retrieval algorithm changes (drop-off, MMR)

**Frontend status**: The `frontend/` directory is a **demo only**. It is not maintained, not documented, and not part of core functionality. RAGex is a backend-first system accessed via CLI or API.

---

## Enforcement Strategy

**Where to add guards**:
- Add assertions only where violations would be **catastrophic**
- Prefer comments documenting invariants over excessive runtime checks
- Use existing validation (config, type hints) instead of new assertions

**What NOT to do**:
- Do not add assertions in hot paths (per-query checks)
- Do not duplicate validation that Pydantic already enforces
- Do not create abstraction layers "for future flexibility"

**When invariants are violated**:
- Fail loudly with clear error message
- Include recovery instructions when possible
- Never silently degrade or auto-fix

---

## Modification Policy

**To change an invariant**:
1. Update this document first
2. Ensure all affected code has clear comments
3. Update tests to verify new behavior
4. Document in tasks.md why the change was necessary

**Red flags** (indicates regression):
- Query operations writing to vector store
- Provider-specific error handling
- Config reads outside config.py
- Multiple indexing pipelines
- Auto-magical index repairs

---

*This is a living document that defines RAGex's frozen scope. Changes to invariants require explicit justification and comprehensive documentation.*
