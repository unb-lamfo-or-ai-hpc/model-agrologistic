"""Directed, product-specific interhub repair using only eligible physical arcs.

The nearest-fraction baseline is preserved. Two rooted shortest-path trees
add connectivity in both directions; edge costs prioritize the number of
excluded arcs, then road distance. This is deterministic, not a globally
minimum-cardinality network design. Potential connectivity does not establish
connectivity after candidate closures, throughput feasibility or travel time.
"""

from __future__ import annotations

import csv
import json
from collections import deque
from dataclasses import replace
from heapq import heappop, heappush
from math import isfinite
from pathlib import Path

from src.logic.model_data import ModelData
from src.logic.route_filtering import SelectedRoutes

ARTIFACTS = (
    "interhub_connectivity_audit.json", "interhub_components.csv",
    "interhub_repair_edges.csv", "interhub_path_summary.csv",
)


def _adjacency(nodes, edges, reverse=False):
    graph = {node: [] for node in sorted(nodes)}
    for source, target in sorted(edges):
        if reverse:
            source, target = target, source
        graph[source].append(target)
    return graph


def components(nodes, edges):
    """Return stable strongly connected components, including isolated hubs."""
    graph = _adjacency(nodes, edges)
    reverse = _adjacency(nodes, edges, True)
    visited, order = set(), []
    for start in graph:
        if start in visited:
            continue
        visited.add(start)
        stack = [(start, iter(graph[start]))]
        while stack:
            node, children = stack[-1]
            target = next(children, None)
            if target is None:
                order.append(node)
                stack.pop()
            elif target not in visited:
                visited.add(target)
                stack.append((target, iter(graph[target])))
    visited, groups = set(), []
    for start in reversed(order):
        if start in visited:
            continue
        visited.add(start)
        stack, group = [start], []
        while stack:
            node = stack.pop()
            group.append(node)
            for target in reverse[node]:
                if target not in visited:
                    visited.add(target)
                    stack.append(target)
        groups.append(sorted(group))
    return sorted(groups)


def _tree(nodes, eligible, selected, distances, reverse=False):
    graph = _adjacency(nodes, eligible, reverse)
    root = min(nodes)
    best, parent = {root: (0, 0.0)}, {}
    queue = [(0, 0.0, root)]
    while queue:
        added, distance, node = heappop(queue)
        if best[node] != (added, distance):
            continue
        for target in graph[node]:
            edge = (target, node) if reverse else (node, target)
            score = (added + int(edge not in selected), distance + distances[edge])
            if target not in best or score < best[target]:
                best[target] = score
                parent[target] = edge
                heappush(queue, (*score, target))
    if len(best) != len(nodes):
        raise ValueError("Eligible interhub graph is not strongly connected; no repair exists.")
    return set(parent.values())


def repair_interhub(data: ModelData, selected: SelectedRoutes) -> SelectedRoutes:
    """Preserve existing routes and add audited forward/reverse tree connectors."""
    nodes = set(data.warehouses)
    dd = set(selected.dd)
    for product in sorted(data.products):
        eligible = {(a, b) for a, b, p in data.routes_dd if p == product and a != b}
        for edge in eligible:
            if not set(edge) <= nodes:
                raise ValueError("Interhub edge references an unknown warehouse.")
            value = data.dist_dd.get(edge)
            if value is None or not isfinite(value) or value < 0:
                raise ValueError(f"Invalid interhub distance: {edge}.")
        current = {(a, b) for a, b, p in dd if p == product}
        if not current <= eligible:
            raise ValueError("Selected interhub edge is not eligible.")
        if len(nodes) <= 1 or len(components(nodes, current)) == 1:
            continue
        if len(components(nodes, eligible)) != 1:
            raise ValueError(f"Eligible interhub graph is not strongly connected for {product}.")
        forward = _tree(nodes, eligible, current, data.dist_dd)
        backward = _tree(nodes, eligible, current | forward, data.dist_dd, reverse=True)
        dd.update((a, b, product) for a, b in forward | backward)
    return replace(selected, dd=dd, repair_dd=selected.repair_dd | (dd - selected.dd))


def build_interhub_audit(data, baseline, before_repair, final, fraction):
    """Describe exact baseline/final fractions and all-pairs minimum-hop reachability."""
    nodes = set(data.warehouses)
    records, component_rows, edge_rows, path_rows = [], [], [], []
    for product in sorted(data.products):
        eligible = {(a, b) for a, b, p in data.routes_dd if p == product and a != b}
        base = {(a, b) for a, b, p in baseline.dd if p == product}
        before = {(a, b) for a, b, p in before_repair.dd if p == product}
        after = {(a, b) for a, b, p in final.dd if p == product}
        counts = {}
        for phase, edges in (("nearest_fraction", base), ("customer_repaired", before),
                             ("interhub_repaired", after)):
            groups = components(nodes, edges)
            counts[phase] = len(groups)
            for index, group in enumerate(groups):
                component_rows.extend({"product": product, "phase": phase,
                                       "component": index, "warehouse": node,
                                       "component_size": len(group)} for node in group)
        for source, target in sorted(after - base):
            edge_rows.append({"product": product, "source": source, "destination": target,
                              "distance_km": data.dist_dd[source, target],
                              "reason": ("customer_coverage" if (source, target) in before
                                         else "interhub_strong_connectivity")})
        graph = _adjacency(nodes, after)
        for source in sorted(nodes):
            hops, queue = {source: 0}, deque([source])
            while queue:
                node = queue.popleft()
                for target in graph[node]:
                    if target not in hops:
                        hops[target] = hops[node] + 1
                        queue.append(target)
            distances = [value for node, value in hops.items() if node != source]
            path_rows.append({"product": product, "source": source,
                              "reachable_other_hubs": len(distances),
                              "unreachable_other_hubs": len(nodes) - 1 - len(distances),
                              "maximum_minimum_hops": max(distances, default=0),
                              "mean_minimum_hops": (sum(distances) / len(distances)
                                                    if distances else 0.0)})
        records.append({"product": product, "warehouses": len(nodes),
                        "eligible_edges": len(eligible), "baseline_edges": len(base),
                        "customer_repair_edges": len(before - base),
                        "interhub_repair_edges": len(after - before),
                        "final_edges": len(after), "requested_fraction": fraction,
                        "baseline_fraction": len(base) / len(eligible) if eligible else 0.0,
                        "final_fraction": len(after) / len(eligible) if eligible else 0.0,
                        "component_counts": counts,
                        "strongly_connected": counts["interhub_repaired"] <= 1})
    return {"schema_version": "interhub-connectivity-v1",
            "scope": "potential_warehouse_graph_by_product",
            "algorithm": "nearest_fraction_plus_rooted_bidirectional_tree_repair",
            "active_network_connectivity_guaranteed": False,
            "throughput_feasibility_guaranteed": False,
            "status": "accepted" if all(r["strongly_connected"] for r in records) else "rejected",
            "products": records, "components": component_rows,
            "repair_edges": edge_rows, "path_summary": path_rows}


def write_interhub_audit(audit, output_dir):
    """Write the four research products without serializing invalid JSON numbers."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    summary = {k: v for k, v in audit.items() if k not in
               {"components", "repair_edges", "path_summary"}}
    (output / ARTIFACTS[0]).write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n",
                                     encoding="utf-8")
    fields = {
        "components": ["product", "phase", "component", "warehouse", "component_size"],
        "repair_edges": ["product", "source", "destination", "distance_km", "reason"],
        "path_summary": ["product", "source", "reachable_other_hubs", "unreachable_other_hubs",
                         "maximum_minimum_hops", "mean_minimum_hops"],
    }
    for name, filename in zip(fields, ARTIFACTS[1:], strict=True):
        with (output / filename).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields[name])
            writer.writeheader()
            writer.writerows(audit[name])
