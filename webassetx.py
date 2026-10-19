#!/usr/bin/env python3
"""
WebAssetX - Website Asset Extractor.

Author  : MrHacker-X
Repo    : https://github.com/MrHacker-X/webassetx
Version : 1.0.0
"""
from __future__ import annotations

import argparse
import sys

from core.config import load_defaults
from core.engine import *  # noqa: F401,F403
from core.utils import *  # noqa: F401,F403

_defaults = load_defaults()
__version__ = str(_defaults.get("version", "1.0.0"))
TOOL_DESC = str(_defaults.get("description", "Target public website URL"))
TOOL_NAME = str(_defaults.get("name", "WebAssetX"))


def register_subparser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("url", nargs="?", help="Target public website URL")
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory (default: ./extracted_assets)",
    )
    parser.add_argument(
        "-c",
        "--categories",
        nargs="+",
        choices=list(ALL_CATEGORIES) + ["all"],
        default=["all"],
        help="Asset categories to extract: images svgs fonts css js or all",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Number of concurrent download workers (default: 6)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="HTTP request timeout in seconds (default: 15)",
    )
    parser.set_defaults(func=run_cli)


def run_cli(args: argparse.Namespace) -> int:
    if not getattr(args, "url", None):
        run_interactive()
        return 0

    cats = list(ALL_CATEGORIES) if "all" in args.categories else args.categories
    print_tool_header("WebAssetX", "Website Asset Extractor", icon="🌐")
    print_info(f"Scanning [bold]{args.url}[/bold] for categories: {', '.join(cats)}")
    try:
        summary = extract_website_assets(
            url=args.url,
            output_dir=args.output,
            categories=cats,
            max_workers=args.workers,
            timeout=args.timeout,
        )
        display_extraction_summary(summary)
        print_success(f"Assets organized in: {summary.output_dir}")
        return 0
    except Exception as exc:
        print_error(f"Extraction failed: {exc}")
        return 1


def run_interactive() -> None:
    print_tool_header("WebAssetX", "Website Asset Extractor", icon="🌐")
    while True:
        choice = prompt_menu(
            "Menu",
            [
                ("1", "Extract all assets"),
                ("2", "Selective extract"),
                ("3", "Preview only"),
                ("a", "About"),
            ],
        )
        if choice == "0":
            return
        if choice == "a":
            show_about_panel()
            console.input("[dim]Press Enter to return to the menu...[/dim]")
            continue

        url = prompt_text("Enter public website URL (e.g. https://example.com)")
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        if choice == "3":
            try:
                resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)
                resp.raise_for_status()
                discovered = discover_assets_from_html(resp.text, resp.url or url)
                counts: Dict[str, int] = {c: 0 for c in ALL_CATEGORIES}
                for item in discovered:
                    counts[item.category] = counts.get(item.category, 0) + 1
                rows = [(cat.upper(), str(counts[cat])) for cat in ALL_CATEGORIES]
                console.print(
                    make_table(
                        f"Discovered Assets on {url}",
                        [("Category", "bold cyan"), ("Count", "bold white")],
                        rows,
                    )
                )
            except Exception as exc:
                print_error(f"Could not inspect URL: {exc}")
            continue

        selected_cats = list(ALL_CATEGORIES)
        if choice == "2":
            raw_cats = prompt_text(
                "Enter categories separated by commas (images, svgs, fonts, css, js)",
                default="images,svgs,fonts,css,js",
            )
            parsed_cats = [c.strip().lower() for c in raw_cats.split(",") if c.strip().lower() in ALL_CATEGORIES]
            if parsed_cats:
                selected_cats = parsed_cats

        out_dir = prompt_text("Output directory", default="extracted_assets")
        try:
            summary = extract_website_assets(
                url=url,
                output_dir=out_dir,
                categories=selected_cats,
            )
            display_extraction_summary(summary)
            print_success(f"Completed! Output saved to {summary.output_dir}")
        except Exception as exc:
            print_error(f"Asset extraction failed: {exc}")



# ----------------------------------------------------------------------------
# CLI main
# ----------------------------------------------------------------------------



def build_arg_parser() -> argparse.ArgumentParser:
    """Build the standalone CLI parser for webassetx."""
    parser = argparse.ArgumentParser(
        prog="webassetx",
        description=TOOL_DESC,
        epilog=(
            "GitHub: https://github.com/MrHacker-X/webassetx - "
            "Run without flags to launch the interactive terminal menu."
        ),
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=TOOL_NAME + " " + __version__,
    )
    parser.add_argument(
        "-a",
        "--about",
        action="store_true",
        help="Show the About screen - overview, key features, version, author and contacts - and exit",
    )
    register_subparser(parser)
    return parser


def main(argv=None) -> int:
    """Entry point: parse flags and dispatch, or launch the interactive menu."""
    try:
        if argv is None:
            argv = sys.argv[1:]
        if not argv:
            # Plain `python webassetx.py` opens the interactive terminal menu.
            run_interactive()
            return 0
        parser = build_arg_parser()
        args = parser.parse_args(argv)
        if getattr(args, "about", False):
            show_about_panel()
            return 0
        func = getattr(args, "func", run_cli)
        result = func(args)
        return int(result) if isinstance(result, (int, float)) else 0
    except (KeyboardInterrupt, EOFError):
        return handle_keyboard_interrupt()


if __name__ == "__main__":
    raise SystemExit(main())
