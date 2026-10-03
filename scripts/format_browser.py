"""Format authored JavaScript and CSS using tools installed through Python."""

import argparse
from pathlib import Path

import cssbeautifier
import jsbeautifier

ROOT = Path(__file__).resolve().parents[1]


def format_files(check: bool) -> bool:
    """Check or apply formatting; leave generated and third-party files alone."""
    dirty = []
    options = jsbeautifier.default_options()
    options.indent_size = 2
    css_options = cssbeautifier.default_options()
    css_options.indent_size = 2
    for path in sorted((ROOT / "src").glob("*")):
        if ".schema." in path.name or path.suffix not in {
            ".js",
            ".css",
        }:
            continue
        original = path.read_text()
        formatter = (
            cssbeautifier.beautify if path.suffix == ".css" else jsbeautifier.beautify
        )
        selected = css_options if path.suffix == ".css" else options
        formatted = formatter(original, selected).rstrip() + "\n"
        if formatted != original:
            dirty.append(str(path.relative_to(ROOT)))
            if not check:
                path.write_text(formatted)
    if dirty and check:
        print("Formatting needed: " + ", ".join(dirty))
        return False
    print("Browser formatting: ok")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raise SystemExit(0 if format_files(args.check) else 1)
