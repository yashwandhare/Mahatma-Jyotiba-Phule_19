# RAGex CLI User Guide

A plain-English guide to using RAGex from the command line.

---

## What is the CLI?

The CLI (Command Line Interface) is a way to use RAGex by typing commands in a terminal window.

If you've never used a terminal before, don't worry. This guide assumes no prior experience.

---

## Opening a Terminal

**On macOS:**
- Press `Cmd + Space`
- Type "Terminal"
- Press Enter

**On Linux:**
- Press `Ctrl + Alt + T`
- Or find "Terminal" in your applications menu

**On Windows (with WSL):**
- Search for "Ubuntu" or "WSL" in the Start menu
- Click to open

---

## Basic Concepts

### What RAGex Does

RAGex reads your documents and answers questions about them.

If the answer is in your documents, RAGex tells you the answer and shows you where it found it.

If the answer is NOT in your documents, RAGex says so instead of making something up.

### What "Indexing" Means

Before RAGex can answer questions, it needs to read your documents and organize them. This is called "indexing."

Indexing happens once. After that, RAGex can answer many questions without reading everything again.

---

## The Most Important Command

```bash
ragex documents/
```

Replace `documents/` with the path to your files.

This command:
1. Reads all files in that folder
2. Organizes them for quick searching
3. Waits for you to ask a question

**Example:**

```bash
ragex ~/Desktop/research/
```

After indexing completes, you'll see a prompt where you can type questions:

```
❯ What is the main topic?
```

Type your question and press Enter. RAGex will answer using information from your documents.

To exit, type `exit` or press `Ctrl+D`.

---

## Common Commands

### Ask One Question and Exit

If you just want to ask one question without starting an interactive session:

```bash
ragex documents/ --ask "What is this about?"
```

RAGex will:
1. Index your documents (if needed)
2. Answer your question
3. Exit

### Clear and Rebuild the Index

If you've added or changed files, you might want to rebuild the index:

```bash
ragex documents/ --clear-index
```

This tells RAGex to forget the old index and create a new one.

### Get a Summary

To see a summary of all your documents:

```bash
ragex documents/ --summary
```

RAGex will read through everything and give you an overview of the main points.

### Describe Your Documents

To understand what your documents are about:

```bash
ragex documents/ --describe
```

This is useful when you've just indexed files and want to know what information is available.

### View Your Settings

To see how RAGex is configured:

```bash
ragex config
```

This shows:
- Which language model you're using
- Where your index is stored
- Other technical settings

You don't need to memorize these. Just run this command if you're curious.

### Clear the Index

To delete your current index:

```bash
ragex clean
```

This removes all indexed documents. Your original files are NOT deleted—only the index that RAGex created.

---

## Offline Mode

### What Offline Mode Means

Normally, RAGex sends your questions to a remote service (Groq) to generate answers. This requires an internet connection.

Offline mode lets RAGex work without the internet by using a local language model (Ollama) on your computer.

### Why Use Offline Mode

- You don't have an internet connection
- You want complete privacy
- You want faster responses (no network delay)

### How to Use Offline Mode

**First, install Ollama:**

1. Visit [ollama.ai](https://ollama.ai)
2. Download and install for your system
3. Open a terminal and run:

```bash
ollama pull llama3.1
```

This downloads a language model to your computer. It's large (a few gigabytes), so it will take a few minutes.

**Then use RAGex offline:**

```bash
ragex documents/ --offline
```

RAGex will now use your local Ollama installation instead of the internet.

---

## Understanding Answers

### When RAGex Finds an Answer

You'll see:
- The answer itself
- A list of sources (which files the information came from)
- Page numbers or line numbers showing exactly where RAGex found the information

**Example output:**

```
Answer

A microprocessor is a small electronic component that contains
the central processing unit of a computer on a single chip.

Sources
# Source
1 computer_basics.pdf (page 12)
2 hardware_guide.txt (lines 45-95)
```

### When RAGex Doesn't Find an Answer

If your documents don't contain the answer, you'll see:

```
✖ Refusal

Answer: Not found in indexed documents.
```

This is intentional. RAGex refuses to guess. If it doesn't know, it says so.

---

## Common Situations

### "I want to search multiple folders"

Index them all at once:

```bash
ragex folder1/ folder2/ folder3/
```

### "I want to index specific files, not a whole folder"

You can specify individual files:

```bash
ragex document.pdf notes.txt research.md
```

### "I indexed the wrong files"

Use `ragex clean` to clear the index, then index the correct files:

```bash
ragex clean
ragex correct_folder/
```

### "My files changed and I want RAGex to notice"

Re-index with the `--clear-index` flag:

```bash
ragex documents/ --clear-index
```

### "RAGex is showing me too much technical information"

That's verbose mode. It's probably on by mistake. Make sure you're NOT using the `--verbose` flag.

### "The output has no colors"

Use the default settings. If colors are disabled, you might have used the `--no-color` flag or set the `NO_COLOR` environment variable.

Colors help you read the output more easily, so use them unless you have a specific reason not to.

---

## Advanced Options

These are optional. You don't need them for normal use.

### Choosing a Provider

RAGex can use different language models:

**Groq (default):**
- Requires internet
- Fast
- Requires API key

**Ollama (local):**
- No internet required
- Runs on your computer
- Must be installed separately

To choose:

```bash
ragex documents/ --provider ollama
```

### Choosing a Model

Each provider has different models available:

```bash
ragex documents/ --provider groq --model llama-3.1-70b-versatile
```

```bash
ragex documents/ --provider ollama --model llama3.1
```

You don't need to specify a model. RAGex has sensible defaults.

### Debug Information

If something isn't working, use verbose mode:

```bash
ragex documents/ --verbose
```

This shows technical details that can help diagnose problems.

### Plain Text Output

If you're using RAGex in a script or you don't want colors:

```bash
ragex documents/ --no-color
```

---

## File Types RAGex Understands

RAGex can read:

**Documents:**
- PDF files (`.pdf`)
- Text files (`.txt`)
- Markdown (`.md`)

**Code:**
- Python (`.py`)
- JavaScript (`.js`)
- TypeScript (`.ts`)
- Java (`.java`)
- C/C++ (`.c`, `.cpp`, `.h`)
- Go (`.go`)
- Rust (`.rs`)
- Ruby (`.rb`)
- PHP (`.php`)

**Configuration:**
- JSON (`.json`)
- YAML (`.yaml`, `.yml`)
- XML (`.xml`)

**Scripts:**
- Shell scripts (`.sh`)
- Bash (`.bash`)
- Zsh (`.zsh`)

If you try to index a file type not listed here, RAGex will skip it and continue with the files it understands.

---

## Troubleshooting

### "Command not found: ragex"

The RAGex command isn't in your PATH. Try:

```bash
python ragcli.py documents/
```

Or run the installer again to set up the command properly.

### "GROQ_API_KEY not configured"

You need an API key to use Groq. Either:

1. Get a free key from [console.groq.com](https://console.groq.com)
2. Edit your `.env` file and add: `GROQ_API_KEY=your_key_here`

Or use Ollama instead:

```bash
ragex documents/ --provider ollama --offline
```

### "Vector store unavailable"

The index is corrupted. Clear it and try again:

```bash
ragex clean
ragex documents/
```

### "Ollama connection failed"

Make sure Ollama is running:

```bash
ollama serve
```

Leave this running in one terminal window, then use RAGex in another window.

### "No valid documents found"

RAGex didn't find any files it can read in the folder you specified. Check:

1. Is the folder path correct?
2. Are there actually files in that folder?
3. Are the files in a supported format? (See "File Types" above)

---

## Tips for Better Results

### Write Clear Questions

Instead of: "Tell me stuff"
Try: "What is the main argument in these papers?"

Instead of: "Code?"
Try: "What does the UserService class do?"

### Use Summaries for Overview

When you first index documents, try:

```bash
ragex documents/ --describe
```

This helps you understand what information is available before asking specific questions.

### Index Related Documents Together

Keep documents about the same topic in one folder and index them together. This helps RAGex give better answers because it sees the full context.

### Remember RAGex Only Knows Your Documents

Don't ask RAGex questions about things not in your documents. It will (correctly) refuse to answer.

If you ask "What is the capital of France?" but your documents are about physics, RAGex will say it doesn't know. This is the right behavior.

---

## Privacy and Security

### What Stays on Your Computer

- All your original documents
- The indexed database
- Your question history (only in interactive mode, not saved)

### What Goes Over the Internet

**When using Groq:**
- Your questions
- Small excerpts from your documents (the relevant passages RAGex found)

**When using Ollama with --offline:**
- Nothing. Everything stays on your computer.

### Your Documents Are Never Uploaded

RAGex never uploads your complete documents. Even when using Groq, only small relevant passages are sent along with your question.

---

## Getting More Help

- Read [QUICK_START.md](QUICK_START.md) for installation help
- Read [INVARIANTS.md](INVARIANTS.md) to understand what RAGex guarantees
- Read [RPD.md](RPD.md) for technical architecture details
- Use `ragex --help` to see all available commands

---

**Remember:** RAGex is a tool for getting reliable answers from your documents. If it doesn't know something, it will tell you. This honesty is what makes RAGex useful.
