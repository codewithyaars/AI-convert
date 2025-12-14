from __future__ import annotations

import argparse
import sys
from typing import TextIO

from csv2json.converter import convert_csv_text, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csv2json",
        description="Convert CSV input to JSON.",
    )

    parser.add_argument(
        "input",
        nargs="?",
        help="Input CSV file path. If omitted, reads from stdin.",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output JSON file path. If omitted, writes to stdout.",
    )

    parser.add_argument(
        "--delimiter",
        default=",",
        help="CSV delimiter (default: ,)",
    )

    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Input file encoding (default: utf-8)",
    )

    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    return parser


def _open_input(args: argparse.Namespace, stdin: TextIO) -> TextIO:
    if args.input:
        return open(args.input, encoding=args.encoding, newline="")
    return stdin


def _open_output(args: argparse.Namespace, stdout: TextIO) -> TextIO:
    if args.output:
        return open(args.output, "w", encoding="utf-8", newline="")
    return stdout


def main(
    argv: list[str] | None = None,
    *,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    in_fp: TextIO | None = None
    out_fp: TextIO | None = None

    try:
        in_fp = _open_input(args, stdin)
        data = convert_csv_text(in_fp, delimiter=args.delimiter)

        out_fp = _open_output(args, stdout)
        write_json(data, out_fp, pretty=args.pretty)
        return 0
    except BrokenPipeError:
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=stderr)
        return 1
    finally:
        # Only close real files we opened (never close caller-provided stdio streams).
        if in_fp is not None and in_fp is not stdin:
            in_fp.close()
        if out_fp is not None and out_fp is not stdout:
            out_fp.close()


if __name__ == "__main__":
    raise SystemExit(main())
