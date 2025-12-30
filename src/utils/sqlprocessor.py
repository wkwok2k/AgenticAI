import csv
import json
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Set, Tuple

from utils.logconfig import step_log
from utils.yaml_loader import render_sql_from_yaml

HopRow = Dict[str, str]


def iter_hops_from_csv(csv_filename: str) -> Iterable[HopRow]:
    """Yield hop rows from a CSV file with prev_hop_id/hop_id/next_hop_id columns."""
    with open(csv_filename, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield {
                "prev_hop_id": str(row.get("prev_hop_id", "") or ""),
                "hop_id": str(row.get("hop_id", "") or ""),
                "next_hop_id": str(row.get("next_hop_id", "") or ""),
            }


def iter_hops_from_json_obj(obj: Dict[str, Any]) -> Iterable[HopRow]:
    """Yield hop rows from an in-memory JSON object (expects obj["paths"] list)."""
    for row in obj.get("paths", []):
        yield {
            "prev_hop_id": str(row.get("prev_hop_id", "") or ""),
            "hop_id": str(row.get("hop_id", "") or ""),
            "next_hop_id": str(row.get("next_hop_id", "") or ""),
        }


def iter_hops_from_json_file(json_filename: str) -> Iterable[HopRow]:
    """Yield hop rows from a JSON file that contains a top-level "paths" list."""
    with open(json_filename, "r", encoding="utf-8") as f:
        obj = json.load(f)
    yield from iter_hops_from_json_obj(obj)


async def generate_sql(yaml_file: str, params: Dict) -> str | None:
    """Generate SQL text from a YAML template and parameters."""
    try:
        sql = render_sql_from_yaml(yaml_file, **params)
        if sql is None:
            step_log("SQL generation returned None")
        return sql
    except Exception as e:
        step_log(f"Error generating SQL: {e}")
        return None

def build_graph_and_starts_from_rows(rows: Iterable[HopRow]) -> Tuple[Dict[str, Set[str]], Set[str]]:
    graph: Dict[str, Set[str]] = defaultdict(set)  # node -> set(next nodes)
    starts: Set[str] = set()                       # nodes whose prev_hop_id is empty

    for row in rows:
        prev = (row.get("prev_hop_id") or "").strip()
        hop  = (row.get("hop_id") or "").strip()
        nxt  = (row.get("next_hop_id") or "").strip()

        if not hop:
            continue

        # Mark starts
        if not prev:
            starts.add(hop)
        else:
            graph[prev].add(hop)

        # Link hop -> next
        if nxt:
            graph[hop].add(nxt)

    return graph, starts


def dfs_paths(graph: Dict[str, Set[str]], start: str) -> List[List[str]]:
    paths: List[List[str]] = []

    def dfs(node: str, path: List[str], visited: Set[str]) -> None:
        # Leaf node (no outgoing edges)
        if node not in graph or not graph[node]:
            paths.append(path[:])
            return

        for nxt in graph[node]:
            if nxt in visited:
                continue
            visited.add(nxt)
            dfs(nxt, path + [nxt], visited)
            visited.remove(nxt)

    dfs(start, [start], {start})
    return paths


def build_paths_from_rows(rows: Iterable[HopRow]) -> List[List[str]]:
    graph, starts = build_graph_and_starts_from_rows(rows)
    all_paths: List[List[str]] = []
    for start in sorted(starts):
        all_paths.extend(dfs_paths(graph, start))
    return all_paths
