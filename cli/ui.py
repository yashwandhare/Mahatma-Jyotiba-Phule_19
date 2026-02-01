"""Shared Rich UI helpers for RAGex CLI entry points."""

from __future__ import annotations

import sys
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.spinner import Spinner
from rich.live import Live

_console: Console | None = None


def configure_console(no_color: bool = False) -> Console:
    """Configure global console instance with TTY detection."""
    global _console
    # Respect NO_COLOR environment variable
    import os
    force_no_color = no_color or os.getenv("NO_COLOR") is not None
    
    # Detect if we're in a real terminal
    is_tty = sys.stdout.isatty()
    
    _console = Console(
        color_system=None if force_no_color else ("auto" if is_tty else None),
        no_color=force_no_color or not is_tty,
        force_terminal=is_tty,
        force_interactive=is_tty
    )
    return _console


def get_console() -> Console:
    if _console is None:
        return configure_console()
    return _console


def print_logo(provider: str, model: str | None, offline: bool, version: str = "1.0.0") -> None:
    """Display minimal ASCII logo with system info."""
    console = get_console()
    
    # Compact ASCII wordmark
    logo = """
██████   █████   ██████  ███████ ██   ██ 
██   ██ ██   ██ ██       ██       ██ ██  
██████  ███████ ██   ███ █████     ███   
██   ██ ██   ██ ██    ██ ██       ██ ██  
██   ██ ██   ██  ██████  ███████ ██   ██
"""
    
    # System info
    model_display = f" ({model})" if model else ""
    status_parts = [f"{provider}{model_display}"]
    if offline:
        status_parts.append("offline")
    status_line = " • ".join(status_parts)
    
    console.print(logo, style="cyan", highlight=False)
    console.print(f"v{version} • {status_line}", style="dim")
    console.print()


def print_phase(text: str, icon: str = "ℹ", style: str = "cyan") -> None:
    """Print a phase indicator."""
    console = get_console()
    console.print(f"{icon} {text}", style=style)


def print_success(text: str) -> None:
    """Print success message."""
    console = get_console()
    console.print(f"✔ {text}", style="green")


def print_warning(text: str) -> None:
    """Print warning message."""
    console = get_console()
    console.print(f"⚠ {text}", style="yellow")


def print_error(text: str) -> None:
    """Print error message."""
    console = get_console()
    console.print(f"✖ {text}", style="red")


def print_info(text: str) -> None:
    """Print informational message."""
    console = get_console()
    console.print(text, style="dim")


def create_spinner(text: str) -> Live:
    """Create a spinner for long operations."""
    console = get_console()
    spinner = Spinner("dots", text=text, style="cyan")
    return Live(spinner, console=console, transient=True)


def render_indexing_summary(result) -> None:
    """Render indexing results in a clean summary panel."""
    console = get_console()
    
    # Build summary table
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Label", style="dim")
    table.add_column("Value", style="green")
    
    table.add_row("Documents indexed", str(result.documents_indexed))
    table.add_row("Chunks created", str(result.chunks_indexed))
    table.add_row("Collection size", str(result.final_index_size))
    
    if result.files_skipped > 0:
        table.add_row("Files skipped", f"{result.files_skipped} [yellow](unsupported)[/yellow]")
    
    if result.index_cleared:
        table.add_row("Previous chunks", f"{result.chunks_removed} [dim](cleared)[/dim]")
    
    console.print(Panel(table, title="✔ Indexing Complete", border_style="green", padding=(1, 2)))
    console.print()


def render_answer(answer: str, sources: List[str]) -> None:
    """Render answer content and sources consistently."""
    console = get_console()
    answer = answer or "No answer returned."
    is_refusal = "not found in indexed documents" in answer.lower()

    panel_title = "✖ Refusal" if is_refusal else "Answer"
    border_style = "yellow" if is_refusal else "cyan"
    text_style = "" if is_refusal else ""

    answer_text = Text(answer, style=text_style)
    console.print(Panel(answer_text, title=panel_title, border_style=border_style, padding=(1, 2)))

    if sources:
        console.print()
        table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE, show_lines=False)
        table.add_column("#", justify="right", width=3, style="dim")
        table.add_column("Source", overflow="fold")
        for idx, src in enumerate(sources, 1):
            display = src if len(src) <= 80 else "..." + src[-77:]
            table.add_row(str(idx), display)
        console.print(table)
    elif not is_refusal:
        console.print(Text("No sources.", style="dim"))


def render_config_table(config_dict: dict, show_secrets: bool = False) -> None:
    """Render configuration as a professional table."""
    console = get_console()
    
    # Group configs by category
    categories = {
        "Provider": ["RAG_PROVIDER", "RAG_MODEL_NAME", "GROQ_API_KEY", "OLLAMA_BASE_URL", "OFFLINE_MODE", "LLM_TIMEOUT"],
        "Storage": ["VECTOR_DB_PATH", "COLLECTION_NAME", "EMBEDDING_MODEL_NAME"],
        "Retrieval": ["CANDIDATE_K", "MIN_SCORE_THRESHOLD", "DROP_OFF_THRESHOLD"],
        "Generation": ["REFUSAL_RESPONSE", "GENERATION_TEMPERATURE", "GENERATION_MAX_TOKENS"],
    }
    
    for category, keys in categories.items():
        table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE, show_lines=False)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", overflow="fold")
        table.add_column("Source", justify="right", style="dim")
        
        for key in keys:
            if key in config_dict:
                info = config_dict[key]
                value = str(info["value"])
                
                # Highlight non-default values
                is_default = str(value) == str(info["default"])
                value_style = "dim" if is_default else "green"
                source_icon = "[dim]●[/dim]" if is_default else "[green]●[/green]"
                
                # Show masked secrets
                if not show_secrets and key.endswith("_KEY") and value and value != "None":
                    value = "●●●●●●●●" + value[-4:]
                
                table.add_row(key, f"[{value_style}]{value}[/{value_style}]", source_icon)
        
        console.print(Panel(table, title=category, border_style="cyan", padding=(1, 2)))
    
    # Show secrets hint
    if not show_secrets:
        has_secrets = any(
            key.endswith("_KEY") and config_dict[key]["value"] not in [None, "None"]
            for key in config_dict
        )
        if has_secrets:
            console.print()
            print_info("ℹ Secrets are masked. Use --show-secrets to reveal.")


__all__ = [
    "configure_console", "get_console", 
    "print_logo", "print_phase", "print_success", "print_warning", "print_error", "print_info",
    "create_spinner", "render_indexing_summary", "render_answer", "render_config_table"
]
