import argparse
import sys
from pathlib import Path
import types

# Provide lightweight stubs so imports work even if optional dependencies are not installed in the test environment.
if "jinja2" not in sys.modules:
    class _MockTemplate:
        def __init__(self, template: str):
            self.template = template

        def render(self, **kwargs):
            return self.template

    sys.modules["jinja2"] = types.SimpleNamespace(Template=_MockTemplate)

if "yaml" not in sys.modules:
    sys.modules["yaml"] = types.SimpleNamespace(safe_load=lambda *_args, **_kwargs: {})

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from utils.sqlprocessor import build_paths_from_rows, iter_hops_from_json_file

FEEDS_DIR = PROJECT_ROOT / "src" / "mcp_server" / "feeds"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build hop lineage from a feed and run date.")
    parser.add_argument("feed_name", help="Feed identifier, e.g., 2052a~Loans")
    parser.add_argument("as_of_date", help="As-of date in YYYYMMDD format, e.g., 20251015")
    return parser.parse_args(argv)


def build_lineage(feed_name: str, as_of_date: str):
    feed_file = FEEDS_DIR / f"hops_{feed_name}_{as_of_date}.json"
    rows = iter_hops_from_json_file(str(feed_file))
    return build_paths_from_rows(rows)


def test_build_lineage_from_minimal_cli_args():
    args = parse_args(["2052a~Loans", "20251015"])
    lineage_paths = build_lineage(args.feed_name, args.as_of_date)

    expected_paths = {
        ("3", "2095", "16*", "21*"),
        ("4*", "16*", "21*"),
        ("9", "2095", "16*", "21*"),
        ("581", "21*"),
        ("5019", "2095", "16*", "21*"),
        ("2094", "2095", "16*", "21*"),
        ("2096", "2095", "16*", "21*"),
    }

    assert {tuple(path) for path in lineage_paths} == expected_paths


def test_feed_file_discoverable_from_args():
    args = parse_args(["2052a~Loans", "20251015"])
    feed_path = FEEDS_DIR / f"hops_{args.feed_name}_{args.as_of_date}.json"

    assert feed_path.is_file()
