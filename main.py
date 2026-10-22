"""Local development entry point: `python main.py` (same as `python -m gateway`)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from gateway.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
