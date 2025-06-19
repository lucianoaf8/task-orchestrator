"""Helper script for scheduled tasks.
Writes a timestamp and optional marker line to the specified output file.

This replaces brittle inline ``python -c`` one-liners previously embedded in
schtasks \TR strings.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:  # noqa: D401
    """Return parsed CLI arguments."""

    parser = argparse.ArgumentParser(description="Write marker line to output file")
    parser.add_argument("--out", required=True, help="Target output file path")
    parser.add_argument("--marker", default="", help="Optional marker text")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:  # noqa: D401
    """Entry point. Returns process exit code."""

    args = _parse_args(argv)

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)

    timestamp = _dt.datetime.now().isoformat(sep=" ", timespec="seconds")
    content = f"SUCCESS at {timestamp}\n{args.marker}"

    output.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
