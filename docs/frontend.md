# RAGex Frontend Documentation

## Goal

Build a **simple, reliable web interface** to interact with the RAG backend.

The frontend must:

* Accept a question
* Display the answer
* Display citations
* Display refusal clearly
* NOT hallucinate or decorate content

This is **not a chat app**.
This is **not a dashboard**.
This is a **QA interface with sources**.

---

## Target Users

* Judges
* Demo audience
* Technical reviewers

Assume:

* Users are not authenticated
* Users may ask bad questions
* Refusal is a valid outcome

---

## Core UI Components (Required)

### 1. Header

* Project name: **RAGex**
* Subtitle (optional):
  *Document-grounded Question Answering*

No logos, no animations.

---

### 2. Question Input

* Single multiline text box
* Placeholder text:

  ```
  Ask a question about the indexed documents…
  ```
* Submit button labeled: **Ask**

Behavior:

* Disable submit if input is empty
* Clear previous answer on new submit
* Show loading state (“Searching documents…”)

---

### 3. Answer Display

Displayed after backend response.

#### Case A: Answer Found

* Show answer text plainly
* No markdown rendering beyond basic line breaks
* No emojis
* No confidence score (optional, backend-driven only)

#### Case B: Refusal

When backend returns:

```
Answer: Not found in indexed documents.
```

Frontend must:

* Display this message verbatim
* Style it neutrally (gray text or warning box)
* Do NOT rephrase
* Do NOT suggest guesses

This is intentional and correct behavior.

---

### 4. Sources / Citations Section (MANDATORY)

Always shown when answer is found.

Format example:

```
Sources:
- design.pdf (page 3)
- auth.py (lines 42–67)
```

Rules:

* One source per line
* No hyperlinks unless file is downloadable
* Display exactly what backend returns
* Do NOT summarize sources

---

## API Interaction

### Endpoint (expected)

```
POST /api/query
```

### Request Body

```json
{
  "question": "string"
}
```

### Response (example)

```json
{
  "answer": "string",
  "sources": [
    "file1.pdf (page 2)",
    "file2.py (lines 10–34)"
  ]
}
```

### Response (refusal)

```json
{
  "answer": "Not found in indexed documents.",
  "sources": []
}
```

Frontend must:

* Trust backend
* Never fabricate UI-level answers
* Never hide refusal

---

## UI Style Guidelines

* Minimalist
* White or dark neutral background
* Monospace or system font
* Clear separation:

  * Question
  * Answer
  * Sources

Avoid:

* Animations
* Chat bubbles
* Avatars
* Typing effects
* Model names (do not show Groq, Llama, etc.)

---

## Explicit Non-Goals (Do NOT add)

* No authentication
* No history sidebar
* No file upload UI (handled elsewhere)
* No document previews
* No edit/delete document buttons
* No analytics
* No fancy state management

If it’s not required for the demo, it should not exist.

---

## Error Handling

### Backend error

* Show generic message:

  ```
  Something went wrong. Please try again.
  ```

### Empty response

* Treat as refusal
* Display refusal message

---

## Success Criteria (Frontend is DONE when…)

* A judge can:

  1. Ask a question
  2. Get an answer
  3. See where the answer came from
  4. See refusal when appropriate

If all four happen, frontend is complete.

---

## Development Notes

* Plain HTML + JS is acceptable
* React/Vite is optional
* Prioritize clarity over architecture
* Backend drives all intelligence

---
