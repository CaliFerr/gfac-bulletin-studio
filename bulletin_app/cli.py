from __future__ import annotations

import argparse
import sys

from .bulletin_pdf import build_bulletin_pdf
from .data import load_program_entries
from .slides import generate_slides


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a church bulletin PDF and PowerPoint slides from CSV data."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    pdf_parser = subparsers.add_parser("pdf", help="Generate the two-column bulletin PDF.")
    pdf_parser.add_argument("csv", help="Path to the source CSV file.")
    pdf_parser.add_argument("output", help="Path to the output PDF.")
    pdf_parser.add_argument(
        "--heading",
        default="Program",
        help="Section heading to print above the generated program content.",
    )

    slides_parser = subparsers.add_parser("slides", help="Generate PowerPoint slides from a template.")
    slides_parser.add_argument("csv", help="Path to the source CSV file.")
    slides_parser.add_argument("template", help="Path to the PowerPoint template.")
    slides_parser.add_argument("output", help="Path to the output PPTX.")

    if len(sys.argv) == 1:
        parser.print_help()
        print()
        print("Examples:")
        print("  python main.py pdf sample_program.csv output/program.pdf")
        print("  python main.py slides sample_program.csv template.pptx output/program_slides.pptx")
        return 0

    args = parser.parse_args()

    if args.command == "pdf":
        entries = load_program_entries(args.csv)
        output = build_bulletin_pdf(entries, args.output, heading=args.heading)
        print(f"Bulletin PDF created: {output}")
        return 0

    if args.command == "slides":
        output = generate_slides(args.template, args.csv, args.output)
        print(f"PowerPoint created: {output}")
        return 0

    parser.error("Unknown command.")
    return 2


def print_help_and_examples() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a church bulletin PDF and PowerPoint slides from CSV data."
    )
    parser.add_argument("command", nargs="?", help="One of: pdf, slides")
    parser.print_help()
    print()
    print("Examples:")
    print("  python main.py pdf sample_program.csv output/program.pdf")
    print("  python main.py slides sample_program.csv template.pptx output/program_slides.pptx")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
