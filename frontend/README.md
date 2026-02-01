# Frontend - Demo Only

**This directory is not part of RAGex's core system.**

## Status

- **Not maintained**: No bug fixes, feature updates, or compatibility guarantees
- **Demo purpose only**: Showcases API capabilities for presentations
- **Optional**: RAGex is fully functional via CLI and API without this

## Core System

RAGex is a **backend-first system** accessed through:
- **CLI**: `ragex` command with full feature set
- **API**: FastAPI endpoints for integration

The frontend is a minimal HTML/CSS/JS demo that calls the API. Use it for quick demos, but rely on CLI/API for production use.

## Scope

See [INVARIANTS.md](../docs/INVARIANTS.md) for frozen scope and core guarantees.

## Maintenance Policy

- No new frontend features
- No framework migrations (stays vanilla JS)
- No mobile/accessibility/browser compatibility work
- Fixes only if they prevent demos from working at all

## Usage

```bash
cd frontend
python -m http.server 4173
```

Visit `http://localhost:4173`, configure API URL in Settings, and drag files to index.

For reliable, scripted, or production use cases, **use the CLI or API directly**.
