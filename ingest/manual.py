import argparse
import re
import sys
from pathlib import Path

from ingest.captures import insert_captures
from ingest.db import connect
from ingest.log import log
from ingest.scrapers.manual import ManualScraper

_MULTISPACE = re.compile(r" {2,}")
_PER_100G = re.compile(r"per\s*100\s*g", re.I)


def _warn(msg):
    print(f"WARNING: {msg}", file=sys.stderr, flush=True)


def _check_expansion(text):
    # --text passes through the shell, where an unquoted or double-quoted $3
    # expands to an empty positional parameter and the price is silently lost.
    # These are the signatures of that. Warn loudly, do not block.
    if _MULTISPACE.search(text):
        _warn(
            "caption contains a run of two or more spaces. If you used --text, a "
            "shell variable such as $3 may have expanded to empty and stripped a "
            "price. Re-ingest with --stdin, which is immune to shell expansion."
        )
    for m in _PER_100G.finditer(text):
        before = text[: m.start()].rstrip()
        if not before or not before[-1].isdigit():
            _warn(
                "caption has 'per 100g' with no number before it. A price was "
                "probably stripped by the shell. Re-ingest with --stdin."
            )
            break


def _read_text(args):
    if args.stdin:
        return sys.stdin.read().strip() or None
    if args.file:
        return Path(args.file).read_text(encoding="utf-8").strip() or None
    if args.text is not None:
        _check_expansion(args.text)
        return args.text
    return None


def main():
    ap = argparse.ArgumentParser("ingest.manual")
    g = ap.add_argument_group("caption text (choose one; --stdin is safest)")
    g.add_argument("--stdin", action="store_true", help="read caption from stdin (immune to shell expansion)")
    g.add_argument("--file", metavar="PATH", help="read caption from a file")
    g.add_argument("--text", help="caption inline (SHELL-EXPANSION PRONE: $vars are stripped; prefer --stdin)")
    ap.add_argument("--image")
    ap.add_argument("--source-url")
    ap.add_argument("--source-type", default="manual")
    args = ap.parse_args()

    if sum([args.text is not None, args.stdin, bool(args.file)]) > 1:
        ap.error("choose only one of --stdin, --file, --text")

    text = _read_text(args)
    if not text and not args.image:
        ap.error("provide caption text (--stdin, --file, or --text) or --image")

    captures = ManualScraper(
        text=text,
        image_path=args.image,
        source_type=args.source_type,
        source_url=args.source_url,
    ).fetch()

    with connect() as conn:
        results = insert_captures(conn, captures)

    for r in results:
        log(
            "manual.capture",
            content_hash=r["capture"].content_hash,
            id=r["id"],
            inserted=r["inserted"],
            duplicate=not r["inserted"],
        )


if __name__ == "__main__":
    main()
