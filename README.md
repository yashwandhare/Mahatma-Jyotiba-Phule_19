# RAGex

Local-first question answering for your documents.

---

## What is RAGex?

RAGex is a command-line tool that answers questions using only the documents you provide. It indexes files locally, retrieves relevant passages, and generates responses grounded in those passages. When the answer is not in your documents, it refuses instead of guessing.

All processing happens on your machine. No data leaves your system unless you explicitly configure a remote language model.

---

## Why RAGex Exists

Language models hallucinate. They produce confident answers that sound correct but are not. For personal knowledge bases, technical documentation, or any scenario where correctness matters more than convenience, hallucination is unacceptable.

RAGex guarantees that every answer is grounded in a specific document you provided, or it returns no answer at all. This tool exists because guessing is worse than silence.

---

## Key Guarantees

- Answers are grounded in indexed documents or explicitly refused
- Source citations are provided for every response
- No network access in offline mode
- No data uploaded without explicit remote provider configuration
- No behavior changes without user action
- No hidden model calls or background indexing

---

## Installation

```bash
bash install.sh
```

The installer is interactive. It will:

- Create a Python virtual environment
- Install required dependencies
- Generate a configuration file
- Prompt for necessary settings

No manual file editing is required.

---

## Basic Usage

**Index and query documents:**

```bash
ragex docs/
```

This opens an interactive session. Type questions and receive grounded answers.

**Ask a single question:**

```bash
ragex docs/ --ask "What is the main argument?"
```

**Clear the index and rebuild:**

```bash
ragex clean
ragex docs/
```

**Edit configuration:**

```bash
ragex config
```

This opens your configuration file for editing provider, model, or storage settings.

---

## How It Works

RAGex follows a three-step process:

1. **Index** – Documents are parsed, split into overlapping chunks, and stored locally with vector embeddings.
2. **Retrieve** – For each question, the most relevant chunks are identified using semantic similarity.
3. **Answer or Refuse** – A language model generates a response using only the retrieved chunks. If the chunks do not contain sufficient information, the system refuses to answer.

The same behavior applies whether you use the CLI, API, or file browser integration.

---

## Privacy & Offline Mode

**What stays local:**

- All indexed documents
- Vector embeddings
- Retrieved passages
- Generated answers (when using a local model)

**When network is used:**

- Only if you configure a remote language model provider (e.g., Groq)
- Only during answer generation
- Only the retrieved passages and your question are sent, not the entire document set

**Offline mode guarantees:**

```bash
ragex docs/ --offline
```

When offline mode is enabled:

- No network requests are permitted
- Local model (Ollama) must be configured and running
- System will refuse to operate if a remote provider is configured

---

## OS Integration

RAGex includes optional desktop integration for Linux and macOS. Once installed, you can right-click any file or folder and select "Index with RAGex" from the context menu.

This opens a terminal, runs the same CLI tool, and provides the same guarantees as manual invocation. No separate service or background process is required.

---

## Who This Is For

**RAGex is for:**

- Researchers managing personal document collections
- Developers querying internal documentation
- Anyone who needs verifiable answers from a specific corpus
- Users who value correctness over convenience

**RAGex is not for:**

- General-purpose chat assistance
- Real-time web search integration
- Large-scale multi-user deployments
- Users who expect answers to questions outside their document set

---

## Project Status

RAGex is stable and actively usable. The scope is frozen. No additional features are planned unless a bug is discovered or a clear deficiency in the existing scope is identified.

The CLI and API are maintained. The browser frontend is provided for demonstration purposes but is not actively developed.

---

## Further Documentation

- [QUICK_START.md](docs/QUICK_START.md) – Detailed usage examples with screenshots
- [INVARIANTS.md](docs/INVARIANTS.md) – System guarantees and behavioral contracts
- [RPD.md](docs/RPD.md) – Requirements, design decisions, and architecture.