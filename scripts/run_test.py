"""
PFI Graph Test — leave-one-out position test.

For each held-out case:
  - Build an in-memory graph from the FULL timelines of the other cases.
  - Drop in only the FIRST 3 actions of the held-out case.
  - Connect nodes with edges weighted by an explicit force function over
    five dimensions (no embeddings).
  - Report each held-out early action's top neighbors and what
    case + sequence position they occupy.

The test passes if the held-out early actions land in neighborhoods
dominated by escalation events of the *other* cases — meaning the
graph placed them near outcomes they actually went on to experience,
without ever being told the outcome.
"""

import argparse
import json
import math
import os
from datetime import datetime

EVENTS_PATH = "data/events.json"
VIEWER_GRAPHS_DIR = "viewer/graphs"
VIEWER_GRAPHS_JS = "viewer/graphs.js"

EARLY_WINDOW = 3
EDGE_THRESHOLD = 0.5
TOP_K_NEIGHBORS = 5

W_MECHANISM = 0.30
W_JURISDICTION = 0.20
W_SEQ_POS = 0.20
W_AGENCY_LEVEL = 0.20
W_ELAPSED = 0.10

AGENCY_LEVEL = {
    "citizen_action": 0,
    "developer": 1,
    "municipal": 1,
    "county_commissioner": 2,
    "district_court": 3,
    "state_agency": 4,
    "federal_agency": 5,
    "unknown": 2,
}

ESCALATION_MECHANISMS = {
    "court_injunction",
    "health_safety_litigation",
    "fire_code_enforcement",
    "zoning_denial",
    "permit_denial_appeal",
    "emergency_moratorium",
    "commissioner_resolution",
}


def load_events():
    with open(EVENTS_PATH) as f:
        data = json.load(f)
    events = data["events"]
    cases = data["cases"]

    by_case = {}
    for e in events:
        by_case.setdefault(e["case_id"], []).append(e)

    out = []
    for case_id, case_events in by_case.items():
        case_events.sort(key=lambda e: e["date"])
        n = len(case_events)
        prev_date = None
        for i, e in enumerate(case_events):
            e["case_position_index"] = i
            e["case_length"] = n
            e["seq_pos_norm"] = i / max(n - 1, 1)
            e["agency_level"] = AGENCY_LEVEL.get(e["jurisdiction_type"], 2)
            d = datetime.fromisoformat(e["date"])
            e["elapsed_days_since_prior"] = (d - prev_date).days if prev_date else 0
            prev_date = d
            e["node_id"] = f"{case_id}__{i:02d}"
            e["outcome_category"] = cases.get(case_id, {}).get("outcome_category")
            out.append(e)
    return out, cases


def similarity(a, b):
    s_mech = 1.0 if a["mechanism_category"] == b["mechanism_category"] else 0.0
    s_juris = 1.0 if a["jurisdiction_type"] == b["jurisdiction_type"] else 0.0
    s_seq = math.exp(-abs(a["seq_pos_norm"] - b["seq_pos_norm"]) * 3)
    s_agency = math.exp(-abs(a["agency_level"] - b["agency_level"]) / 2)
    ea = max(a["elapsed_days_since_prior"], 1)
    eb = max(b["elapsed_days_since_prior"], 1)
    s_elapsed = math.exp(-abs(math.log(ea) - math.log(eb)) / 2)
    return (
        W_MECHANISM * s_mech
        + W_JURISDICTION * s_juris
        + W_SEQ_POS * s_seq
        + W_AGENCY_LEVEL * s_agency
        + W_ELAPSED * s_elapsed
    )


def build_graph(all_events, held_out_case):
    nodes = [
        e for e in all_events
        if e["case_id"] != held_out_case
        or e["case_position_index"] < EARLY_WINDOW
    ]
    edges = []
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            w = similarity(a, b)
            if w >= EDGE_THRESHOLD:
                edges.append({
                    "source": a["node_id"],
                    "target": b["node_id"],
                    "weight": round(w, 4),
                })
    return nodes, edges


def report_case(held_out_case, nodes, edges, cases):
    by_id = {n["node_id"]: n for n in nodes}
    held_out_early_ids = {
        n["node_id"] for n in nodes if n["case_id"] == held_out_case
    }

    held_out_nodes = sorted(
        [n for n in nodes if n["case_id"] == held_out_case],
        key=lambda n: n["case_position_index"],
    )
    case_meta = cases.get(held_out_case, {})
    outcome_cat = case_meta.get("outcome_category", "unknown")
    print(f"\n{'=' * 72}")
    print(f"HELD-OUT CASE: {held_out_case}  (outcome: {outcome_cat})")
    print(f"Graph: {len(nodes)} nodes, {len(edges)} edges")
    print(f"{'=' * 72}")

    all_neighbor_mechs = []
    all_neighbor_outcomes = []
    held_out_actions = []
    for n in held_out_nodes:
        print(f"\n  Action #{n['case_position_index'] + 1}  "
              f"{n['date']}  [{n['mechanism_category']}]"
              f"  jurisdiction={n['jurisdiction_type']}")
        print(f"    > {n['action_description'][:110]}")

        candidates = []
        for e in edges:
            if e["source"] == n["node_id"]:
                other_id = e["target"]
            elif e["target"] == n["node_id"]:
                other_id = e["source"]
            else:
                continue
            if other_id in held_out_early_ids:
                continue
            candidates.append((e["weight"], by_id[other_id]))
        candidates.sort(key=lambda x: -x[0])
        top = candidates[:TOP_K_NEIGHBORS]

        top_k = []
        if not top:
            print("    (no neighbors above threshold)")
        else:
            print(f"    Top {len(top)} neighbors:")
            for weight, b in top:
                marker = " *" if b["mechanism_category"] in ESCALATION_MECHANISMS else "  "
                outcome = b.get("outcome_category") or "?"
                print(f"     {marker} {weight:.3f}  "
                      f"{b['case_id']:22s}  {b['date']}  "
                      f"{b['mechanism_category']:28s}  "
                      f"{outcome[:8]:8s}  {b['sequence_position']}")
                all_neighbor_mechs.append(b["mechanism_category"])
                all_neighbor_outcomes.append(b.get("outcome_category"))
                top_k.append({
                    "case": b["case_id"],
                    "mechanism": b["mechanism_category"],
                    "outcome": b.get("outcome_category"),
                    "weight": weight,
                    "date": b["date"],
                    "seq_pos": b["sequence_position"],
                    "is_escalation_mech": b["mechanism_category"] in ESCALATION_MECHANISMS,
                })

        held_out_actions.append({
            "idx": n["case_position_index"],
            "date": n["date"],
            "mechanism": n["mechanism_category"],
            "jurisdiction": n["jurisdiction_type"],
            "description": n["action_description"],
            "node_id": n["node_id"],
            "top_k": top_k,
        })

    esc_pct = 0
    clean_pct = 0
    if all_neighbor_mechs:
        total = len(all_neighbor_mechs)
        esc = sum(1 for m in all_neighbor_mechs if m in ESCALATION_MECHANISMS)
        esc_pct = 100 * esc // total
        clean_neigh = sum(1 for o in all_neighbor_outcomes if o == "clean")
        clean_pct = 100 * clean_neigh // total
        print(f"\n  Neighborhood profile: "
              f"{esc}/{total} ({esc_pct}%) escalation-type mechanisms; "
              f"{clean_neigh}/{total} ({clean_pct}%) neighbors from clean cases")
    return {
        "case_id": held_out_case,
        "outcome": outcome_cat,
        "escalation_pct": esc_pct,
        "clean_neighbor_pct": clean_pct,
        "neighbor_count": len(all_neighbor_mechs),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "held_out_actions": held_out_actions,
    }


def export_graph_json(summary, nodes, edges):
    case_id = summary["case_id"]
    os.makedirs(VIEWER_GRAPHS_DIR, exist_ok=True)
    held_out_early_ids = {
        n["node_id"] for n in nodes if n["case_id"] == case_id
    }
    payload = {
        "case_id": case_id,
        "outcome": summary["outcome"],
        "summary": {
            "escalation_pct": summary["escalation_pct"],
            "clean_neighbor_pct": summary["clean_neighbor_pct"],
            "neighbor_count": summary["neighbor_count"],
            "node_count": summary["node_count"],
            "edge_count": summary["edge_count"],
        },
        "held_out_actions": summary["held_out_actions"],
        "nodes": [
            {
                "id": n["node_id"],
                "case_id": n["case_id"],
                "date": n["date"],
                "mechanism": n["mechanism_category"],
                "jurisdiction": n["jurisdiction_type"],
                "seq_pos": n["sequence_position"],
                "outcome": n.get("outcome_category"),
                "is_held_out_early": n["node_id"] in held_out_early_ids,
                "description": n["action_description"][:200],
            }
            for n in nodes
        ],
        "edges": edges,
    }
    path = os.path.join(VIEWER_GRAPHS_DIR, f"{case_id}.json")
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    return path


def write_combined_graphs_js(case_ids):
    combined = {}
    for cid in case_ids:
        path = os.path.join(VIEWER_GRAPHS_DIR, f"{cid}.json")
        if not os.path.exists(path):
            continue
        with open(path) as f:
            combined[cid] = json.load(f)
    os.makedirs(os.path.dirname(VIEWER_GRAPHS_JS), exist_ok=True)
    with open(VIEWER_GRAPHS_JS, "w") as f:
        f.write("window.GRAPHS = ")
        json.dump(combined, f)
        f.write(";\n")
    return VIEWER_GRAPHS_JS


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--case", help="Run only this held-out case")
    args = p.parse_args()

    all_events, cases = load_events()
    case_ids = sorted({e["case_id"] for e in all_events})

    print(f"Loaded {len(all_events)} events across {len(case_ids)} cases.")
    print(f"Force function weights: mech={W_MECHANISM} juris={W_JURISDICTION} "
          f"seq={W_SEQ_POS} agency={W_AGENCY_LEVEL} elapsed={W_ELAPSED}")
    print(f"Edge threshold: {EDGE_THRESHOLD}  Early window: {EARLY_WINDOW} actions  "
          f"Top-K: {TOP_K_NEIGHBORS}")
    print("Legend: '*' = neighbor is an escalation-type mechanism")

    targets = [args.case] if args.case else case_ids
    summaries = []
    exported_cases = []
    for case in targets:
        if case not in case_ids:
            print(f"Unknown case: {case}. Available: {case_ids}")
            continue
        nodes, edges = build_graph(all_events, case)
        summary = report_case(case, nodes, edges, cases)
        export_graph_json(summary, nodes, edges)
        exported_cases.append(case)
        summaries.append(summary)

    if exported_cases:
        write_combined_graphs_js(case_ids)
        print(f"\nViewer data written to {VIEWER_GRAPHS_DIR}/ and {VIEWER_GRAPHS_JS}")

    if len(summaries) > 1:
        print(f"\n{'=' * 72}")
        print("SUMMARY — escalation-% in neighborhood, grouped by outcome")
        print(f"{'=' * 72}")
        order = {"clean": 0, "under_construction": 1, "withdrawn": 2, "escalation": 3}
        summaries.sort(key=lambda s: (order.get(s["outcome"], 99), -s["escalation_pct"]))
        print(f"  {'case_id':24s}  {'outcome':20s}  esc%   clean-neigh%   neighbors")
        for s in summaries:
            print(f"  {s['case_id']:24s}  {s['outcome']:20s}  "
                  f"{s['escalation_pct']:3d}%   {s['clean_neighbor_pct']:3d}%           "
                  f"{s['neighbor_count']}")
        print("\n  Read: clean cases should show LOW escalation-% / HIGH clean-neighbor-%;")
        print("  escalation cases should show the inverse.")

    print(f"\n{'=' * 72}")
    print("Done. Open viewer/index.html in your browser.")


if __name__ == "__main__":
    main()
