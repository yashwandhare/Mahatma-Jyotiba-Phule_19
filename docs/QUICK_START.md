# RAGex Quick Start Guide

Get started with RAGex in under five minutes.

---

## Installation

Run the installer:

```bash
bash install.sh
```

The installer will:
- Create a virtual environment
- Install all dependencies
- Set up configuration
- Prompt for your API key

That's it. RAGex is ready to use.

---

## Your First Query

Index some documents and ask a question:

```bash
ragex documents/
```

This will:
1. Index all files in the `documents/` folder
2. Start an interactive session
3. Wait for your question

Type a question and press Enter. RAGex will answer using only information from your documents.

If the answer is not in your documents, RAGex will refuse instead of guessing.

---

## Basic Commands

**Index and ask one question:**

```bash
ragex documents/ --ask "What is the main topic?"
```

**Clear the old index and rebuild:**

```bash
ragex documents/ --clear-index
```

**Get a summary of all indexed documents:**

```bash
ragex documents/ --summary
```

**Describe what the documents are about:**

```bash
ragex documents/ --describe
```

**View your configuration:**

```bash
ragex config
```

**Clear the index:**

```bash
ragex clean
```

---

## Right-Click Integration (Optional)

After installation, you can right-click any file or folder and select "Index with RAGex" from your system menu.

This opens a terminal and runs the same CLI tool. No separate setup required.

Currently supported:
- Linux (Nautilus file manager)
- macOS (Finder)

---

## Offline Mode

RAGex can run without an internet connection if you have Ollama installed locally.

**Install Ollama:**

Visit [ollama.ai](https://ollama.ai) and follow the installation instructions for your system.

**Download a model:**

```bash
ollama pull llama3.1
```

**Use RAGex offline:**

```bash
ragex documents/ --offline
```

When offline mode is enabled:
- No network requests are made
- All processing happens locally
- Ollama must be running

---

## Using the API (Optional)

## Using the API (Optional)

RAGex includes an HTTP API for integration with other tools.

**Start the API server:**

```bash
source .venv/bin/activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

**Ask a question:**

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this about?"}'
```

**Upload files:**

```bash
curl -X POST http://localhost:8000/upload \
  -F "files=@document.pdf"
```

**Check health:**

```bash
curl http://localhost:8000/health
```

For full API documentation, see the OpenAPI schema at `http://localhost:8000/docs` when the server is running.

---

## Using the Frontend (Optional)

RAGex includes a demonstration browser interface at `frontend/index.html`.

**To use it:**

1. Start the API server (see above)
2. Open `frontend/index.html` in a browser
3. Click Settings and confirm the API URL
4. Drag files to upload

The frontend is provided for demonstration purposes. It is not maintained or covered by system guarantees.

For production use, the CLI is recommended.

---

## Configuration

View your current configuration:

```bash
ragex config
```

This shows all settings including:
- Which provider you're using (Groq or Ollama)
- Which model is active
- Where your index is stored
- Retrieval thresholds
- Generation parameters

To change settings, edit the `.env` file in your RAGex directory.

**Common settings:**

```bash
# .env file

# Which provider to use
PROVIDER=groq

# Which model to use
MODEL=llama-3.1-70b-versatile

# Your Groq API key
GROQ_API_KEY=your_key_here

# Ollama settings (if using Ollama)
OLLAMA_BASE_URL=http://localhost:11434

# Force offline mode
OFFLINE_MODE=false
```

---

## Supported File Types

RAGex can index:

- **Documents:** PDF, TXT, MD
- **Code:** PY, JS, TS, JAVA, CPP, C, H, GO, RS, RB, PHP
- **Config:** JSON, YAML, YML, XML
- **Scripts:** SH, BASH, ZSH

All files are processed locally. Nothing is uploaded unless you explicitly start the API server and use the upload endpoint.

---

## Common Questions

**Q: Do I need an internet connection?**

Only if you're using Groq as your provider. If you use Ollama with `--offline`, everything runs locally.

**Q: What happens to my documents?**

They are indexed and stored in a local database (ChromaDB). Nothing is uploaded unless you explicitly use the API upload endpoint.

**Q: Can I use RAGex with multiple document sets?**

Yes. Use `ragex clean` to clear the current index, then index a new set of documents. Each index replaces the previous one.

**Q: How do I update RAGex?**

Pull the latest code from the repository and run `bash install.sh` again. Your configuration and index are preserved.

**Q: Where is my index stored?**

By default in `./data/vectordb/` inside your RAGex directory. You can change this in `.env` with the `VECTOR_DB_PATH` setting.

---

## Troubleshooting

**"GROQ_API_KEY not configured"**

Edit your `.env` file and add your API key:

```bash
GROQ_API_KEY=your_key_here
```

Get a key from [console.groq.com](https://console.groq.com).

**"Vector store unavailable"**

The index is corrupted. Clear it and rebuild:

```bash
ragex clean
ragex documents/
```

**CLI won't start**

Make sure you activated the virtual environment:

```bash
source .venv/bin/activate
```

Then run RAGex normally.

**Ollama connection failed**

Make sure Ollama is running:

```bash
ollama serve
```

And that you have a model downloaded:

```bash
ollama pull llama3.1
```

---

## Next Steps

- Read [cli.md](cli.md) for detailed command explanations
- Read [INVARIANTS.md](INVARIANTS.md) to understand system guarantees
- Read [RPD.md](RPD.md) for technical architecture details
