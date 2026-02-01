#!/usr/bin/env python3
"""RAGex CLI - production-grade entry point."""

import argparse
import logging
import os
import sys
import time
from typing import List, Tuple
from pathlib import Path
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from io import StringIO

from cli.ui import (
    configure_console, 
    render_answer, 
    print_logo, 
    print_phase, 
    print_success, 
    print_warning, 
    print_error, 
    print_info,
    create_spinner,
    render_indexing_summary,
    render_config_table,
    get_console
)
from backend.app.core.errors import get_error_message


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



def print_vector_store_unavailable():
    """Display a friendly message when the vector store cannot be accessed."""
    print_error(get_error_message('vector_store_unavailable'))
    print_info("Run 'ragex clean' to rebuild the index and try again.")
    print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ragex",
        description="Index documents and ask grounded questions with one command.",
    )

    parser.add_argument(
        "paths",
        nargs="*",
        help="File and folder paths to index before answering",
    )
    parser.add_argument("--ask", help="Index (if needed) and answer one question", type=str, metavar="QUESTION")
    parser.add_argument("--summary", help="Summarize the indexed documents", action="store_true")
    parser.add_argument("--describe", help="Describe what the indexed documents cover", action="store_true")
    parser.add_argument("--clear-index", help="Clear the index before processing new files", action="store_true")
    parser.add_argument("--provider", help="LLM provider to use", choices=["groq", "ollama"], default="groq")
    parser.add_argument("--model", help="LLM model name for the chosen provider", type=str, metavar="NAME")
    parser.add_argument("--offline", help="Force offline mode (Ollama only)", action="store_true")
    parser.add_argument("--verbose", help="Show debug logs", action="store_true")
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
    warnings.filterwarnings(
        "ignore",
        message="You are sending unauthenticated requests to the HF Hub.*",
    )


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
    from backend.app.rag import retriever, generator, indexer, store

    return retriever, generator, indexer, store



def get_interactive_paths() -> Tuple[List[str], bool]:
    """Interactively prompt for file/folder paths.

    Returns the collected paths and whether the user chose to reuse the existing index.
    """
    console = get_console()
    console.print("Document Selection", style="bold cyan")
    print_info("Enter a path per line. Press Enter immediately to reuse the existing index.")
    console.print()

    paths: List[str] = []
    try:
        while True:
            prompt = f"{Colors.BLUE}❯{Colors.RESET} " if not paths else f"{Colors.DIM}❯{Colors.RESET} "
            line = input(prompt).strip()

            if not line:
                if not paths:
                    print_info("Using existing index without changes")
                    console.print()
                    return [], True
                break

            paths.append(line)
            print(f"{Colors.DIM}  ✔ Added{Colors.RESET}")

    except KeyboardInterrupt:
        print_info("\nCancelled")
        sys.exit(0)

    console.print()
    return paths, False


def run_config_command(argv: List[str] | None = None):
    """Handle the `ragex config` command - show effective configuration."""
    config_parser = argparse.ArgumentParser(
        prog="ragex config",
        description="Display effective RAGex configuration",
    )
    config_parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    config_parser.add_argument("--show-secrets", action="store_true", help="Show full API keys (use carefully)")

    args = config_parser.parse_args(argv)

    configure_console(args.no_color)
    if args.no_color:
        Colors.disable()

    # Import config after environment is set
    from backend.app.core.config import get_config_dict

    console = get_console()
    console.print("\nRAGex Configuration", style="bold cyan")
    print_info("Effective values (defaults → .env → environment)")
    console.print()

    config_dict = get_config_dict(mask_secrets=not args.show_secrets)
    render_config_table(config_dict, show_secrets=args.show_secrets)
    console.print()


def run_clean_command(argv: List[str] | None = None):
    """Handle the `ragex clean` command."""
    clean_parser = argparse.ArgumentParser(
        prog="ragex clean",
        description="Safely clear the RAGex vector index",
    )
    clean_parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    clean_parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    args = clean_parser.parse_args(argv)

    configure_console(args.no_color)
    if args.no_color:
        Colors.disable()

    configure_logging(args.verbose)

    console = get_console()
    console.print()
    print_phase("RAGex Index Cleaner", icon="🧹")
    console.print()

    try:
        from backend.app.rag import indexer, store as store_mod
        removed = indexer.clean_index()
        if removed:
            print_success(f"Cleared index ({removed} chunk(s) removed)")
        else:
            print_info("Index was already empty")
    except store_mod.IndexStateError:
        print_vector_store_unavailable()
        sys.exit(1)
    except Exception as exc:
        logging.exception("Failed to clear index", exc_info=exc)
        if args.verbose:
            raise
        print_error(get_error_message('index_clean_failed'))
        sys.exit(1)
    console.print()
    sys.exit(0)


def run_indexing(indexer_mod, paths: List[str], clear_index: bool):
    """Index documents into vector store."""
    console = get_console()

    # Show what we're indexing
    console.print("Indexing", style="bold cyan")
    for p in paths:
        name = Path(p).name
        print_info(f"  • {name}")
    console.print()
    
    start = time.time()

    # Run canonical indexing pipeline with spinner
    with create_spinner("Loading documents..."):
        result = indexer_mod.index_paths(paths, clear_index=clear_index)

    elapsed = time.time() - start

    # Show any warnings
    if result.index_cleared:
        print_info(f"Cleared existing index (removed {result.chunks_removed} chunk(s))")

    if result.files_skipped:
        print_warning(f"Skipped {result.files_skipped} file(s) (unsupported format)")

    if result.documents_indexed == 0:
        print_error(get_error_message('no_valid_documents'))
        print_info("  Supported: PDF, TXT, MD, code files")
        sys.exit(1)

    # Show summary
    render_indexing_summary(result)
    print_info(f"Completed in {elapsed:.1f}s")
    console.print()
    return result



def run_query(retriever, generator, store_mod, question: str, verbose: bool = False, intent=None):
    """Execute a single query with intent support."""
    from backend.app.rag.intent import detect_intent, get_retrieval_strategy, QueryIntent
    console = get_console()
    
    if not question or not question.strip():
        return

    # Detect or use explicit intent
    if intent:
        query_intent = intent
    else:
        query_intent = detect_intent(question)
    
    intent_label = query_intent.value if hasattr(query_intent, 'value') else str(query_intent)
    
    # Show progress with spinner
    start = time.time()
    
    # Get retrieval strategy
    strategy = get_retrieval_strategy(query_intent)
    
    try:
        # Retrieve and generate - suppress HF model loading output
        with suppress_output(verbose), create_spinner(f"Processing ({intent_label})..."):
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
    except store_mod.IndexStateError:
        print_vector_store_unavailable()
        return

    # Render results
    console.print()
    render_answer(gen_res.get("answer", ""), gen_res.get("sources", []))
    
    elapsed = time.time() - start
    console.print()
    print_info(f"Completed in {elapsed:.1f}s • intent: {intent_label}")
    console.print()


def repl_loop(retriever, generator, store_mod, verbose: bool = False):
    """Interactive REPL for questions."""
    console = get_console()
    print_success("Ready")
    print_info("Type your question (or 'exit' to quit)")
    console.print()
    
    try:
        while True:
            try:
                q = input(f"{Colors.BLUE}❯{Colors.RESET} ").strip()
            except EOFError:
                break
                
            if q.lower() in {"exit", "quit", "q"}:
                break
            if not q:
                continue
                
            run_query(retriever, generator, store_mod, q, verbose)
            
    except KeyboardInterrupt:
        console.print()
        print_info("Goodbye")
        console.print()


def main(argv: List[str] | None = None):
    """Main CLI entry point."""
    if argv is None:
        argv = sys.argv[1:]

    store_mod = None

    # Handle subcommands
    if argv and argv[0] == "clean":
        run_clean_command(argv[1:])
        return
    
    if argv and argv[0] == "config":
        run_config_command(argv[1:])
        return

    parser = build_parser()
    args = parser.parse_args(argv)

    configure_console(args.no_color)

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
    
    # Show logo for interactive sessions
    if not args.ask:
        print_logo(args.provider, args.model, args.offline)

    # Load backend modules (suppress import logs)
    console = get_console()
    try:
        if not args.verbose:
            with create_spinner("Initializing..."):
                retriever, generator, indexer_mod, store_mod = load_backend()
        else:
            retriever, generator, indexer_mod, store_mod = load_backend()
            
    except Exception as exc:
        logging.exception("Failed to load backend", exc_info=exc)
        if args.verbose:
            raise
        print_error(get_error_message('backend_init_failed'))
        sys.exit(1)

    # Determine paths to index
    paths_to_index: List[str] = list(args.paths)
    reused_existing = False
    interactive_mode = not (args.ask or args.summary or args.describe)

    if not paths_to_index and interactive_mode:
        paths_to_index, reused_existing = get_interactive_paths()

    indexing_result = None

    # Index documents if paths provided
    if paths_to_index:
        try:
            indexing_result = run_indexing(indexer_mod, paths_to_index, args.clear_index)
        except store_mod.IndexStateError:
            print_vector_store_unavailable()
            sys.exit(1)
        except Exception as exc:
            logging.exception("Indexing failed", exc_info=exc)
            if args.verbose:
                raise
            print_error(get_error_message('indexing_failed'))
            sys.exit(1)
    else:
        # No paths provided
        if args.ask:
            print_info("Answering question using the existing index")
            console.print()
        elif args.summary:
            print_info("Summarizing the existing index")
            console.print()
        elif args.describe:
            print_info("Describing the existing index")
            console.print()
        elif not reused_existing:
            print_info("Using existing index without changes")
            console.print()

    if interactive_mode:
        if indexing_result:
            print_info("Entering Q&A mode with freshly indexed documents")
        else:
            print_info("Entering Q&A mode with existing index")
        console.print()

    # Execute query or start REPL
    if args.ask:
        run_query(retriever, generator, store_mod, args.ask, args.verbose)
    elif args.summary:
        from backend.app.rag.intent import QueryIntent
        summary_query = "Summarize the main points and key information from these documents."
        run_query(retriever, generator, store_mod, summary_query, args.verbose, intent=QueryIntent.SUMMARY)
    elif args.describe:
        from backend.app.rag.intent import QueryIntent
        describe_query = "What are these documents about? Describe their main topics and purpose."
        run_query(retriever, generator, store_mod, describe_query, args.verbose, intent=QueryIntent.DESCRIPTION)
    else:
        repl_loop(retriever, generator, store_mod, args.verbose)


if __name__ == "__main__":  # pragma: no cover
    main()