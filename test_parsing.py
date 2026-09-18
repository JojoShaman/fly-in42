#!/usr/bin/env python3
"""Run the parser against every map in a test directory and report results.

Usage:
    python3 test_parsing.py maps/broken2

Files named `9x_valid_*.txt` are expected to parse successfully.
Every other file is expected to raise (a parsing error).
Anything that doesn't match that expectation, or crashes with an
unhandled exception, is flagged.
"""
import sys
import traceback
from pathlib import Path
from io import StringIO
from contextlib import redirect_stdout

sys.path.insert(0, "src")
from src.parsing import Parsing  # noqa: E402


def run_one(path: Path) -> tuple[str, str]:
    """Parse a single file and classify the outcome.

    Returns:
        (status, detail) where status is one of:
        'ok'        - parsed successfully
        'rejected'  - raised ValueError (a handled parsing error)
        'crash'     - raised something else (a bug)
    """
    buf = StringIO()
    try:
        with redirect_stdout(buf):
            Parsing().parse(str(path))
        return ("ok", "")
    except ValueError:
        return ("rejected", buf.getvalue().strip())
    except Exception:
        return ("crash", traceback.format_exc())


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python3 test_parsing.py <maps_dir>")
        sys.exit(1)

    directory = Path(sys.argv[1])
    files = sorted(directory.glob("*.txt"))
    if not files:
        print(f"no .txt files found in {directory}")
        sys.exit(1)

    failures = 0
    for f in files:
        expected_valid = f.stem.startswith(tuple(f"9{i}" for i in range(10)))
        status, detail = run_one(f)

        if status == "crash":
            print(f"💥 CRASH   {f.name}")
            print(detail)
            failures += 1
        elif expected_valid and status != "ok":
            print(f"❌ SHOULD PASS  {f.name}")
            print(f"   {detail.splitlines()[0] if detail else ''}")
            failures += 1
        elif not expected_valid and status == "ok":
            print(f"❌ SHOULD FAIL  {f.name}  (parsed without error)")
            failures += 1
        else:
            mark = "✅" if status == "ok" else "✓ "
            print(f"{mark} {f.name}")

    print()
    print(f"{len(files)} files, {failures} unexpected result(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
