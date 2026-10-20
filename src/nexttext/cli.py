"""Command-line interface for ``nexttext``.

Examples:
    nexttext debias input.txt
    nexttext debias --jsonl --field caption captions.jsonl
    nexttext inject-bias --strategy contextual --output rebiased.txt input.txt

The CLI has no third-party dependencies.  It reads stdin when the input path is
``-`` (the default) and writes stdout when ``-o/--output`` is omitted.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, TextIO

from nexttext import __version__
from nexttext.bias import debias, inject_bias
from nexttext.strategies import available_strategies

_PROGRAM = "nexttext"


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the CLI and return a process exit code.

    Args:
        argv: Argument list, defaulting to ``sys.argv[1:]``.

    Returns:
        ``0`` on success, ``2`` for usage/input errors.
    """

    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "strategies":
        for name in available_strategies():
            print(name)
        return 0
    try:
        if args.command == "debias":
            return _run_debias(args)
        if args.command == "inject-bias":
            return _run_inject_bias(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"{_PROGRAM}: error: {exc}", file=sys.stderr)
        return 2
    parser.print_help(sys.stderr)
    return 2


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser."""

    parser = argparse.ArgumentParser(
        prog=_PROGRAM,
        description="Neutralize or reintroduce gendered language in text.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    debias_parser = subparsers.add_parser(
        "debias",
        help="neutralize gendered terms",
        description="Neutralize gendered terms in plain text or JSONL.",
    )
    _add_common_arguments(debias_parser)
    debias_parser.add_argument(
        "--flag-only",
        action="store_true",
        help="annotate low-confidence rewrites instead of applying them",
    )
    debias_parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.8,
        metavar="FLOAT",
        help="minimum confidence for a rewrite in --flag-only mode (default: 0.8)",
    )
    debias_parser.add_argument(
        "--structured",
        action="store_true",
        help="include rule, confidence, and flag metadata in JSON output",
    )

    rebias_parser = subparsers.add_parser(
        "inject-bias",
        help="reintroduce gendered terms",
        description="Reintroduce gendered terms in plain text or JSONL.",
    )
    _add_common_arguments(rebias_parser)

    subparsers.add_parser(
        "strategies",
        help="list registered strategies",
        description="List the names accepted by --strategy.",
    )
    return parser


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments shared by ``debias`` and ``inject-bias``."""

    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="input file, or - for stdin (default: -)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="-",
        help="output file, or - for stdout (default: -)",
    )
    parser.add_argument(
        "--strategy",
        default="default",
        help="registered strategy name (default: default)",
    )
    parser.add_argument(
        "--locale",
        default="en",
        help="built-in locale when no lexicon is supplied (default: en)",
    )
    parser.add_argument(
        "--lexicon",
        action="append",
        default=[],
        metavar="PATH",
        help="JSON/YAML lexicon override; may be repeated",
    )
    parser.add_argument(
        "--proper-noun",
        action="append",
        default=[],
        metavar="WORD",
        help="exact proper noun to leave untouched; may be repeated",
    )
    parser.add_argument(
        "--jsonl",
        action="store_true",
        help="read and write JSON Lines instead of plain text",
    )
    parser.add_argument(
        "--field",
        default="text",
        help="JSONL field containing the input text (default: text)",
    )
    parser.add_argument(
        "--output-field",
        default=None,
        help="JSONL field to write the result to (default: same as --field)",
    )


def _run_debias(args: argparse.Namespace) -> int:
    """Execute the ``debias`` subcommand."""

    lexicon = list(args.lexicon) or None
    proper_nouns = list(args.proper_noun) or None

    def transform(values: List[str]) -> List[Any]:
        return debias(
            values,
            proper_nouns=proper_nouns,
            strategy=args.strategy,
            lexicon=lexicon,
            locale=args.locale,
            flag_only=args.flag_only,
            confidence_threshold=args.confidence_threshold,
            structured=args.structured,
        )

    return _process(args, transform, structured=args.structured)


def _run_inject_bias(args: argparse.Namespace) -> int:
    """Execute the ``inject-bias`` subcommand."""

    lexicon = list(args.lexicon) or None

    def transform(values: List[str]) -> List[str]:
        return inject_bias(
            values,
            strategy=args.strategy,
            lexicon=lexicon,
            locale=args.locale,
        )

    return _process(args, transform, structured=False)


def _process(
    args: argparse.Namespace,
    transform: Callable[[List[str]], List[Any]],
    *,
    structured: bool,
) -> int:
    """Read input, apply ``transform``, and write output."""

    input_text = _read_input(args.input)
    output_handle, should_close = _open_output(args.output)
    try:
        if args.jsonl:
            return _process_jsonl(
                input_text,
                output_handle,
                transform,
                field=args.field,
                output_field=args.output_field or args.field,
                structured=structured,
            )
        return _process_plain(
            input_text,
            output_handle,
            transform,
            structured=structured,
        )
    finally:
        if should_close:
            output_handle.close()


def _process_plain(
    text: str,
    output: TextIO,
    transform: Callable[[List[str]], List[Any]],
    *,
    structured: bool,
) -> int:
    """Apply ``transform`` line by line while preserving line endings."""

    lines = text.splitlines(keepends=True)
    contents = [_strip_line_ending(line) for line in lines]
    endings = [_line_ending(line) for line in lines]
    results = transform(contents)

    if structured:
        payload = [result.to_dict() for result in results]
        json.dump(payload, output, ensure_ascii=False, indent=2)
        output.write("\n")
        return 0

    for result, ending in zip(results, endings):
        output.write(str(result))
        output.write(ending)
    return 0


def _process_jsonl(
    text: str,
    output: TextIO,
    transform: Callable[[List[str]], List[Any]],
    *,
    field: str,
    output_field: str,
    structured: bool,
) -> int:
    """Apply ``transform`` to a field in each JSONL object."""

    records: List[Dict[str, Any]] = []
    values: List[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict):
            msg = f"line {line_number}: JSONL records must be objects"
            raise ValueError(msg)
        value = record.get(field)
        if not isinstance(value, str):
            msg = f"line {line_number}: field {field!r} must be a string"
            raise ValueError(msg)
        records.append(record)
        values.append(value)

    results = transform(values)
    for record, result in zip(records, results):
        if structured:
            record[output_field] = result.output
            record[f"{output_field}_nexttext"] = result.to_dict()
        else:
            record[output_field] = result
        output.write(json.dumps(record, ensure_ascii=False))
        output.write("\n")
    return 0


def _read_input(path: str) -> str:
    """Read ``path`` or stdin when the path is ``-``."""

    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _open_output(path: str) -> "tuple[TextIO, bool]":
    """Open ``path`` or return stdout when the path is ``-``."""

    if path == "-":
        return sys.stdout, False
    return Path(path).open("w", encoding="utf-8", newline=""), True


def _strip_line_ending(line: str) -> str:
    """Remove a single trailing CRLF, LF, or CR from ``line``."""

    if line.endswith("\r\n"):
        return line[:-2]
    if line.endswith(("\n", "\r")):
        return line[:-1]
    return line


def _line_ending(line: str) -> str:
    """Return the trailing line ending of ``line``, if any."""

    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    if line.endswith("\r"):
        return "\r"
    return ""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
