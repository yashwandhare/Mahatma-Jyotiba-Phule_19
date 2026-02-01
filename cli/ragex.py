import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from ragcli import main as rag_main

    rag_main()


if __name__ == "__main__":  # pragma: no cover
    main()