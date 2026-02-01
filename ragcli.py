#!/usr/bin/env python3
"""RAGex CLI - production-grade entry point."""

import argparse
import logging
import os
import sys
import time
from typing import List
from pathlib import Path
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from io import StringIO


class Colors:
    PINK = "\033[38;2;251;134;213m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls):
        cls.PINK = cls.GREEN = cls.YELLOW = cls.BLUE = cls.GRAY = cls.BOLD = cls.DIM = cls.RESET = ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ragex",
        description="RAGex – Context-aware document QA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ragex documents/                         # Index a folder and start REPL
  ragex file.pdf --ask "What is this about?"  # Index and ask question
  ragex docs/ --summary                    # Generate document summary
  ragex docs/ --describe                   # Describe document contents
  ragex --clear-index docs/                # Rebuild index from scratch
  ragex --offline --provider ollama        # Use local Ollama
        """
    )

    parser.add_argument(
        "paths",
        nargs="*",
        help="Folder(s) or file(s) to index (optional for REPL-only mode)",
    )
    parser.add_argument("--ask", help="Ask a single question after indexing", type=str, metavar="QUESTION")
    parser.add_argument("--summary", help="Generate a summary of indexed documents", action="store_true")
    parser.add_argument("--describe", help="Describe what the indexed documents are about", action="store_true")
    parser.add_argument("--clear-index", help="Clear the vector DB before indexing", action="store_true")
    parser.add_argument("--provider", help="LLM provider (default: groq)", choices=["groq", "ollama"], default="groq")
    parser.add_argument("--model", help="LLM model name (provider-specific)", type=str, metavar="NAME")
    parser.add_argument("--offline", help="Disable remote providers (Groq)", action="store_true")
    parser.add_argument("--verbose", help="Enable debug logging", action="store_true")
    parser.add_argument("--no-color", help="Disable colored output", action="store_true")
    parser.add_argument("--version", action="version", version="RAGex 1.0.0")

    return parser


def configure_logging(verbose: bool):
    """Configure logging with suppression of noisy libraries."""
    if verbose:
        level = logging.DEBUG
        format_str = "%(levelname)s: %(message)s"
    else:
        # Suppress all but critical errors in non-verbose mode
        level = logging.CRITICAL
        format_str = ""
    
    logging.basicConfig(level=level, format=format_str)
    
    # Always silence these noisy libraries
    logging.getLogger("chromadb").setLevel(logging.CRITICAL)
    logging.getLogger("httpx").setLevel(logging.CRITICAL)
    logging.getLogger("openai").setLevel(logging.CRITICAL)
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)
    logging.getLogger("httpcore").setLevel(logging.CRITICAL)
    logging.getLogger("charset_normalizer").setLevel(logging.CRITICAL)
    
    # Silence Hugging Face / Transformers / Sentence Transformers
    logging.getLogger("transformers").setLevel(logging.CRITICAL)
    logging.getLogger("sentence_transformers").setLevel(logging.CRITICAL)
    logging.getLogger("huggingface_hub").setLevel(logging.CRITICAL)
    logging.getLogger("torch").setLevel(logging.CRITICAL)
    logging.getLogger("tensorflow").setLevel(logging.CRITICAL)
    
    # Suppress warnings from these libraries
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", message=".*Torch was not compiled with flash attention.*")


@contextmanager
def suppress_output(verbose: bool = False):
    """Context manager to suppress all stdout/stderr output unless verbose."""
    if verbose:
        yield
        return
    
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            sys.stdout = devnull
            sys.stderr = devnull
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


def apply_env(args: argparse.Namespace):
    """Set environment variables from CLI args."""
    os.environ["RAG_PROVIDER"] = args.provider
    if args.model:
        os.environ["RAG_MODEL_NAME"] = args.model
    if args.offline:
        os.environ["RAG_OFFLINE"] = "1"


def load_backend():
    """Lazy-load backend modules to avoid import-time logs."""
    from backend.app.rag import loader, chunker, store, retriever, generator
    from backend.app.core import config

    return loader, chunker, store, retriever, generator, config


def banner():
    """Display ASCII art banner."""
    art = f"""{Colors.PINK}
██████╗  █████╗  ██████╗ ███████╗██╗  ██╗
██╔══██╗██╔══██╗██╔════╝ ██╔════╝╚██╗██╔╝
██████╔╝███████║██║  ███╗█████╗   ╚███╔╝ 
██╔══██╗██╔══██║██║   ██║██╔══╝   ██╔██╗ 
██║  ██║██║  ██║╚██████╔╝███████╗██╔╝ ██╗
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝{Colors.RESET}
"""
    print(art)
    print(f"{Colors.DIM}Context-Aware Document QA • v1.0.0{Colors.RESET}\n")


def get_interactive_paths() -> List[str]:
    """Interactively prompt user for file/folder paths."""
    print(f"{Colors.BOLD}📁 Document Selection{Colors.RESET}")
    print(f"{Colors.DIM}Enter paths to index (one per line, press Enter twice when done){Colors.RESET}\n")
    
    paths = []
    try:
        while True:
            prompt = f"{Colors.BLUE}❯{Colors.RESET} " if paths else f"{Colors.BLUE}❯{Colors.RESET} "
            line = input(prompt).strip()
            
            if not line:
                if paths:
                    break
                else:
                    print(f"{Colors.YELLOW}⚠ Please provide at least one path{Colors.RESET}")
                    continue
            
            # Expand home directory and resolve path
            expanded = Path(line).expanduser().resolve()
            
            if expanded.exists():
                paths.append(str(expanded))
                print(f"{Colors.DIM}  ✓ Added{Colors.RESET}")
            else:
                print(f"{Colors.YELLOW}  ✗ Not found: {line}{Colors.RESET}")
                retry = input(f"{Colors.DIM}  Try again? (y/n): {Colors.RESET}").lower()
                if retry != 'y':
                    continue
                    
    except KeyboardInterrupt:
        print(f"\n{Colors.DIM}Cancelled{Colors.RESET}")
        sys.exit(0)
    
    print()
    return paths


def validate_paths(paths: List[str]) -> List[str]:
    """Validate and normalize paths."""
    valid = []
    invalid = []
    
    for p in paths:
        if not p or not str(p).strip():
            continue
        
        # Expand and resolve path
        expanded = Path(p).expanduser().resolve()
        
        if not expanded.exists():
            invalid.append(p)
            continue
        
        valid.append(str(expanded))
    
    # Report invalid paths
    if invalid:
        print(f"{Colors.YELLOW}⚠ Skipped {len(invalid)} invalid path(s){Colors.RESET}")
        for p in invalid:
            print(f"{Colors.DIM}  • {p}{Colors.RESET}")
        print()
    
    if not valid:
        print(f"{Colors.YELLOW}✗ No valid paths provided{Colors.RESET}")
        sys.exit(1)
    
    return valid


def run_indexing(loader, chunker_mod, store, paths: List[str], clear_index: bool):
    """Index documents into vector store."""
    collection = store.get_collection()
    existing = collection.count()

    # Handle index clearing
    if clear_index and existing:
        print(f"{Colors.BLUE}🗑  Clearing index ({existing} chunks)...{Colors.RESET}", end=" ", flush=True)
        store.clear_index()
        print(f"{Colors.GREEN}✓{Colors.RESET}")
        existing = 0

    # Skip if already indexed
    if existing and not clear_index:
        print(f"{Colors.GREEN}✓ Index ready ({existing} chunks){Colors.RESET}")
        print(f"{Colors.DIM}  Use --clear-index to rebuild{Colors.RESET}\n")
        return

    # Show what we're indexing
    print(f"{Colors.BOLD}📚 Indexing {len(paths)} path(s){Colors.RESET}")
    for p in paths:
        name = Path(p).name
        print(f"{Colors.DIM}  • {name}{Colors.RESET}")
    print()
    
    start = time.time()

    # Load documents
    print(f"{Colors.BLUE}⏳ Loading documents...{Colors.RESET}", end=" ", flush=True)
    docs = loader.load_inputs(paths)
    
    if not docs:
        print(f"\n{Colors.YELLOW}✗ No documents found{Colors.RESET}")
        print(f"{Colors.DIM}  Supported: PDF, TXT, MD, code files{Colors.RESET}")
        sys.exit(1)
    
    print(f"{Colors.GREEN}✓ {len(docs)}{Colors.RESET}")

    # Chunk documents
    print(f"{Colors.BLUE}⏳ Creating chunks...{Colors.RESET}", end=" ", flush=True)
    chunker_inst = chunker_mod.Chunker()
    chunks = chunker_inst.chunk(docs)
    print(f"{Colors.GREEN}✓ {len(chunks)}{Colors.RESET}")

    # Store in vector DB
    print(f"{Colors.BLUE}⏳ Building index...{Colors.RESET}", end=" ", flush=True)
    store.index_chunks(chunks)
    elapsed = time.time() - start
    print(f"{Colors.GREEN}✓ {elapsed:.1f}s{Colors.RESET}\n")


def render_answer(answer: str, sources: List[str]):
    """Render answer with sources in a clean format."""
    is_refusal = "Not found in indexed documents" in answer
    
    print(f"\n{Colors.BOLD}Answer{Colors.RESET}")
    print("─" * 50)
    
    if is_refusal:
        print(f"{Colors.DIM}{answer}{Colors.RESET}")
    else:
        print(answer)
    
    if sources:
        print(f"\n{Colors.BOLD}Sources{Colors.RESET}")
        print("─" * 50)
        for i, src in enumerate(sources, 1):
            # Truncate long paths
            display = src if len(src) < 60 else "..." + src[-57:]
            print(f"{Colors.DIM}{i}.{Colors.RESET} {display}")


def run_query(retriever, generator, question: str, verbose: bool = False, intent=None):
    """Execute a single query with intent support."""
    from backend.app.rag.intent import detect_intent, get_retrieval_strategy, QueryIntent
    
    if not question or not question.strip():
        return

    # Detect or use explicit intent
    if intent:
        query_intent = intent
    else:
        query_intent = detect_intent(question)
    
    intent_label = query_intent.value if hasattr(query_intent, 'value') else str(query_intent)
    
    # Show minimal progress indicator
    print(f"{Colors.DIM}Thinking ({intent_label})...{Colors.RESET}", end="\r", flush=True)
    start = time.time()

    # Get retrieval strategy
    strategy = get_retrieval_strategy(query_intent)
    
    # Retrieve and generate - suppress HF model loading output
    with suppress_output(verbose):
        retrieval_res = retriever.retrieve(
            question,
            top_k=strategy["top_k"],
            min_similarity=strategy["min_similarity"],
            diverse_sampling=strategy["diverse_sampling"]
        )
        chunks = retrieval_res.get("chunks", [])
        gen_res = generator.generate_answer(
            question,
            chunks,
            intent=query_intent,
            strict_refusal=strategy["strict_refusal"]
        )

    # Clear progress line
    print(" " * 40, end="\r")

    # Render results with intent badge
    badge_color = Colors.BLUE if intent_label != "factual" else Colors.GREEN
    print(f"{badge_color}[{intent_label}]{Colors.RESET}\n")
    render_answer(gen_res.get("answer", ""), gen_res.get("sources", []))
    
    elapsed = time.time() - start
    print(f"\n{Colors.DIM}Completed in {elapsed:.1f}s{Colors.RESET}\n")


def repl_loop(retriever, generator, verbose: bool = False):
    """Interactive REPL for questions."""
    print(f"{Colors.GREEN}✓ Ready{Colors.RESET}")
    print(f"{Colors.DIM}Type your question (or 'exit' to quit){Colors.RESET}\n")
    
    try:
        while True:
            try:
                q = input(f"{Colors.PINK}❯{Colors.RESET} ").strip()
            except EOFError:
                break
                
            if q.lower() in {"exit", "quit", "q"}:
                break
            if not q:
                continue
                
            run_query(retriever, generator, q, verbose)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.DIM}Goodbye{Colors.RESET}")


def main(argv: List[str] | None = None):
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Configure colors and logging FIRST (before any imports)
    if args.no_color:
        Colors.disable()
    
    # Suppress progress bars and other output BEFORE loading backend
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["TRANSFORMERS_VERBOSITY"] = "error"
    os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    os.environ["HF_HUB_DISABLE_EXPERIMENTAL_WARNING"] = "1"
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    os.environ["TQDM_DISABLE"] = "1"  # Disable tqdm progress bars
    
    configure_logging(args.verbose)
    apply_env(args)

    # Show banner unless in single-question mode
    if not args.ask:
        banner()
        provider_display = f"{args.provider}"
        if args.model:
            provider_display += f" ({args.model})"
        print(f"{Colors.DIM}Provider: {provider_display}{Colors.RESET}")
        if args.offline:
            print(f"{Colors.DIM}Mode: Offline{Colors.RESET}")
        print()

    # Load backend modules (suppress import logs)
    try:
        if not args.ask and not args.verbose:
            print(f"{Colors.DIM}Initializing...{Colors.RESET}", end="\r", flush=True)
        
        loader, chunker_mod, store, retriever, generator, config = load_backend()
        
        if not args.ask and not args.verbose:
            print(" " * 40, end="\r")  # Clear "Initializing..."
            
    except Exception as exc:
        print(f"{Colors.YELLOW}✗ Failed to load backend: {exc}{Colors.RESET}")
        if args.verbose:
            raise
        sys.exit(1)

    # Determine paths to index
    paths_to_index = args.paths
    
    if not paths_to_index and not args.ask:
        # Interactive mode: ask user for paths
        paths_to_index = get_interactive_paths()
    
    # Index documents if paths provided
    if paths_to_index:
        valid_paths = validate_paths(paths_to_index)
        run_indexing(loader, chunker_mod, store, valid_paths, args.clear_index)
    else:
        # No paths provided
        if args.ask:
            print(f"{Colors.YELLOW}⚠ No paths provided, querying existing index{Colors.RESET}\n")
        else:
            print(f"{Colors.YELLOW}⚠ No paths provided, using existing index{Colors.RESET}\n")

    # Execute query or start REPL
    if args.ask:
        run_query(retriever, generator, args.ask, args.verbose)
    elif args.summary:
        from backend.app.rag.intent import QueryIntent
        summary_query = "Summarize the main points and key information from these documents."
        run_query(retriever, generator, summary_query, args.verbose, intent=QueryIntent.SUMMARY)
    elif args.describe:
        from backend.app.rag.intent import QueryIntent
        describe_query = "What are these documents about? Describe their main topics and purpose."
        run_query(retriever, generator, describe_query, args.verbose, intent=QueryIntent.DESCRIPTION)
    else:
        repl_loop(retriever, generator, args.verbose)


if __name__ == "__main__":  # pragma: no cover
    main()