# RAGex Quick Start Guide

## 🚀 Getting Started

### 1. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 2. Start the Backend
```bash
# Terminal 1: Start API server
uvicorn backend.app.main:app --reload

# Server runs at http://localhost:8000
```

### 3. Use the System

Choose your interface:

---

## 🖥️ Option 1: Web Interface (Recommended)

**Open:** `frontend/index.html` in your browser

**Features:**
- 💬 Multi-chat like ChatGPT
- 📄 Drag-and-drop file upload
- 📊 Live document statistics
- 🏷️ Intent badges (factual/summary/description)
- 📚 Source citations
- 💾 Persistent chat history

**Workflow:**
1. Click upload area or drag files
2. See documents appear in sidebar
3. Ask questions in chat
4. View intent-aware responses with sources
5. Create new chats for different topics

---

## 💻 Option 2: Command Line

### Basic Usage

```bash
# Index and start interactive mode
python ragcli.py documents/

# Ask a single question
python ragcli.py docs/ --ask "What is a microprocessor?"

# Generate document summary
python ragcli.py research/ --summary

# Describe document contents
python ragcli.py report.pdf --describe
```

### Advanced Options

```bash
# Clear index before re-indexing
python ragcli.py docs/ --clear-index

# Use Ollama instead of Groq
python ragcli.py docs/ --provider ollama --model llama2

# Offline mode (requires Ollama)
python ragcli.py docs/ --offline --provider ollama

# Verbose logging
python ragcli.py docs/ --verbose

# No colored output
python ragcli.py docs/ --no-color
```

---

## 🎯 Query Intent Examples

RAGex automatically detects query intent and adjusts its response strategy:

### Factual Queries (Default)
```
Q: "What is a microprocessor?"
Q: "Who invented the CPU?"
Q: "When was the first computer built?"

→ Strict retrieval with similarity threshold
→ Refuses if answer not in documents
→ Cites specific sources
```

### Summary Queries
```
Q: "Summarize the key points"
Q: "Give me an overview"
Q: "What are the main topics?"

→ Diverse sampling across all documents
→ No similarity threshold
→ Structured summary format
```

### Description Queries
```
Q: "What is this document about?"
Q: "Describe these files"
Q: "Tell me about this content"

→ Representative chunks from documents
→ Focuses on topics and purpose
→ Identifies content type
```

---

## 📡 API Usage

### Ask a Question
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is a CPU?"}'
```

Response:
```json
{
    "answer": "A CPU is...",
    "sources": ["file.pdf (page 1)"],
    "intent": "factual"
}
```

### List Documents
```bash
curl http://localhost:8000/documents
```

Response:
```json
{
    "total_chunks": 142,
    "total_documents": 5,
    "documents": [
        {"filename": "cpu.pdf", "chunk_count": 45},
        {"filename": "memory.pdf", "chunk_count": 38}
    ]
}
```

### Upload Files
```bash
curl -X POST http://localhost:8000/upload \
  -F "files=@document.pdf" \
  -F "files=@readme.txt"
```

### Health Check
```bash
curl http://localhost:8000/health
```

---

## 🎨 Intent Customization

### Explicit Intent Override

**CLI:**
```bash
# Force summary intent
python ragcli.py docs/ --summary

# Force description intent
python ragcli.py docs/ --describe
```

**API:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "About this", "intent": "description"}'
```

**Frontend:**
Intent is auto-detected and shown as a badge in responses.

---

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Required
PROVIDER=groq                           # groq or ollama
MODEL=llama-3.1-70b-versatile          # Model name
GROQ_API_KEY=your_key_here             # Get from console.groq.com

# Optional
CHROMADB_PATH=./chromadb_data          # Database location
COLLECTION_NAME=ragex_docs             # Collection name
OLLAMA_BASE_URL=http://localhost:11434 # Ollama URL
OFFLINE_MODE=false                     # Disable remote providers
```

### Frontend Settings

Click **Settings** button to configure:
- API base URL (default: `http://localhost:8000`)

---

## 📂 Supported File Types

- **Documents:** PDF, TXT, MD
- **Code:** PY, JS, TS, JAVA, CPP, C, H, GO, RS, RB, PHP
- **Config:** JSON, YAML, YML, XML
- **Scripts:** SH, BASH, ZSH

**Max File Size:** 50MB per file

---

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check if dependencies are installed
pip install -r requirements.txt

# Verify .env file exists
ls -la .env

# Check for port conflicts
lsof -i :8000
```

### "GROQ_API_KEY not configured"
```bash
# Edit .env and add your API key
echo "GROQ_API_KEY=your_key_here" >> .env
```

### Frontend can't connect
```bash
# Verify backend is running
curl http://localhost:8000/health

# Check browser console for errors (F12)

# Update API base in Settings if using different port
```

### CLI import errors
```bash
# Ensure you're in the project directory
cd /path/to/RAGex

# Check Python path
python -c "import sys; print(sys.path)"

# Run with full path
python /path/to/RAGex/ragcli.py
```

### Ollama connection failed
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Pull a model
ollama pull llama2
```

---

## 📊 Performance Tips

### For Large Document Sets
```bash
# Clear index periodically
python ragcli.py docs/ --clear-index

# Use offline mode for faster responses
python ragcli.py docs/ --provider ollama --offline
```

### For Better Summaries
```bash
# Ensure documents are well-indexed
# Summaries work best with 5-20 documents

# Use explicit summary flag for clarity
python ragcli.py docs/ --summary
```

### Frontend Performance
- Limit chat history to ~100 messages per chat
- Clear localStorage if sluggish: `localStorage.clear()`
- Use Chrome/Firefox for best performance

---

## 🎓 Example Workflows

### Workflow 1: Research Paper Analysis
```bash
# Index papers
python ragcli.py research_papers/ --clear-index

# Get overview
python ragcli.py research_papers/ --describe

# Generate summary
python ragcli.py research_papers/ --summary

# Ask specific questions
python ragcli.py research_papers/
> What methodology is used?
> What are the key findings?
> exit
```

### Workflow 2: Code Documentation
```bash
# Index codebase
python ragcli.py src/ --clear-index

# Describe the project
python ragcli.py src/ --describe

# Ask about specific components
python ragcli.py src/ --ask "What does the UserService class do?"
```

### Workflow 3: Frontend Multi-Chat
1. Open `frontend/index.html`
2. Upload project documentation
3. Create chat "Architecture Questions"
4. Ask about system design
5. Create new chat "API Reference"
6. Ask about endpoints
7. Switch between chats as needed

---

## 📚 Further Reading

- **Production Upgrade Report:** `PRODUCTION_UPGRADE_REPORT.md`
- **Refactor Report:** `REFACTOR_REPORT.md`
- **Environment Template:** `.env.example`

---

## 💡 Pro Tips

1. **Multi-Chat:** Use separate chats for different topics in frontend
2. **Intent Detection:** Questions starting with "what is" → factual, "summarize" → summary
3. **Batch Upload:** Select multiple files at once in frontend
4. **CLI REPL:** Type `exit` or press Ctrl+D to quit interactive mode
5. **Offline Mode:** Use Ollama for no internet connection required
6. **Settings:** Change API base in frontend for remote backends

---

## 🤝 Getting Help

1. Check this guide
2. Review error messages (use `--verbose` flag)
3. Check browser console (F12) for frontend issues
4. Verify backend health: `curl http://localhost:8000/health`

---

**Version:** 1.0.0  
**Status:** Production Ready ✅
