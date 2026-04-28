"""
PFI Graph Test — leave-one-out position test.

For each of the 4 cases:
  - Build a Neo4j graph from the FULL timelines of the other 3 cases.
  - Drop in only the FIRST 3 actions of the held-out case.
  - Connect nodes with SIMILAR_TO edges weighted by an explicit
    force function over five dimensions (no embeddings).
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
from neo4j import GraphDatabase

EVENTS_PATH = "data/events.json"
VIEWER_GRAPHS_DIR = "viewer/graphs"
VIEWER_GRAPHS_JS = "viewer/graphs.js"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "pfi_graph_test")

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


def build_graph(driver, all_events, held_out_case):
    nodes = [
        e for e in all_events
        if e["case_id"] != held_out_case
        or e["case_position_index"] < EARLY_WINDOW
    ]

    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

        for e in nodes:
            session.run(
                """
                CREATE (n:Action {
                    node_id: $node_id, case_id: $case_id, date: $date,
                    mechanism: $mechanism, jurisdiction_type: $jurisdiction_type,
                    sequence_position: $sequence_position,
                    seq_pos_norm: $seq_pos_norm, agency_level: $agency_level,
                    elapsed_days: $elapsed_days,
                    case_position_index: $case_position_index,
                    outcome_category: $outcome_category,
                    is_held_out_early: $held_out, description: $desc
                })
                """,
                node_id=e["node_id"],
                case_id=e["case_id"],
                date=e["date"],
                mechanism=e["mechanism_category"],
                jurisdiction_type=e["jurisdiction_type"],
                sequence_position=e["sequence_position"],
                seq_pos_norm=e["seq_pos_norm"],
                agency_level=e["agency_level"],
                elapsed_days=e["elapsed_days_since_prior"],
                case_position_index=e["case_position_index"],
                outcome_category=e.get("outcome_category"),
                held_out=(e["case_id"] == held_out_case),
                desc=e["action_description"][:200],
            )

        edge_count = 0
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                w = similarity(a, b)
                if w >= EDGE_THRESHOLD:
                    session.run(
                        """
                        MATCH (a:Action {node_id: $a_id}),
                              (b:Action {node_id: $b_id})
                        CREATE (a)-[:SIMILAR_TO {weight: $w}]->(b)
                        """,
                        a_id=a["node_id"], b_id=b["node_id"], w=round(w, 4),
                    )
                    edge_count += 1

    return nodes, edge_count


def report_case(driver, held_out_case, nodes, edge_count, cases):
    held_out_nodes = sorted(
        [n for n in nodes if n["case_id"] == held_out_case],
        key=lambda n: n["case_position_index"],
    )
    case_meta = cases.get(held_out_case, {})
    outcome_cat = case_meta.get("outcome_category", "unknown")
    print(f"\n{'=' * 72}")
    print(f"HELD-OUT CASE: {held_out_case}  (outcome: {outcome_cat})")
    print(f"Graph: {len(nodes)} nodes, {edge_count} edges")
    print(f"{'=' * 72}")

    with driver.session() as session:
        all_neighbor_mechs = []
        all_neighbor_outcomes = []
        held_out_actions = []
        for n in held_out_nodes:
            print(f"\n  Action #{n['case_position_index'] + 1}  "
                  f"{n['date']}  [{n['mechanism_category']}]"
                  f"  jurisdiction={n['jurisdiction_type']}")
            print(f"    > {n['action_description'][:110]}")

            result = list(session.run(
                """
                MATCH (a:Action {node_id: $node_id})-[r:SIMILAR_TO]-(b:Action)
                WHERE NOT b.is_held_out_early
                RETURN b.case_id AS case, b.mechanism AS mechanism,
                       b.sequence_position AS seq_pos, b.date AS date,
                       b.outcome_category AS outcome,
                       r.weight AS weight, b.description AS desc
                ORDER BY r.weight DESC
                LIMIT $k
                """,
                node_id=n["node_id"], k=TOP_K_NEIGHBORS,
            ))

            top_k = []
            if not result:
                print("    (no neighbors above threshold)")
            else:
                print(f"    Top {len(result)} neighbors:")
                for row in result:
                    marker = " *" if row["mechanism"] in ESCALATION_MECHANISMS else "  "
                    print(f"     {marker} {row['weight']:.3f}  "
                          f"{row['case']:22s}  {row['date']}  "
                          f"{row['mechanism']:28s}  "
                          f"{(row['outcome'] or '?')[:8]:8s}  {row['seq_pos']}")
                    all_neighbor_mechs.append(row["mechanism"])
                    all_neighbor_outcomes.append(row["outcome"])
                    top_k.append({
                        "case": row["case"],
                        "mechanism": row["mechanism"],
                        "outcome": row["outcome"],
                        "weight": round(row["weight"], 4),
                        "date": row["date"],
                        "seq_pos": row["seq_pos"],
                        "is_escalation_mech": row["mechanism"] in ESCALATION_MECHANISMS,
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
            "edge_count": edge_count,
            "held_out_actions": held_out_actions,
        }


def export_graph_json(driver, summary):
    case_id = summary["case_id"]
    os.makedirs(VIEWER_GRAPHS_DIR, exist_ok=True)
    with driver.session() as session:
        nodes = [dict(r) for r in session.run(
            """
            MATCH (n:Action)
            RETURN n.node_id AS id, n.case_id AS case_id, n.date AS date,
                   n.mechanism AS mechanism, n.jurisdiction_type AS jurisdiction,
                   n.sequence_position AS seq_pos,
                   n.outcome_category AS outcome,
                   n.is_held_out_early AS is_held_out_early,
                   n.description AS description
            """
        )]
        edges = [dict(r) for r in session.run(
            """
            MATCH (a:Action)-[r:SIMILAR_TO]->(b:Action)
            RETURN a.node_id AS source, b.node_id AS target, r.weight AS weight
            """
        )]
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
        "nodes": nodes,
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
    p.add_argument("--case", help="Run only this held-out case (leaves graph in Neo4j for inspection)")
    args = p.parse_args()

    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
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
        nodes, edges = build_graph(driver, all_events, case)
        summary = report_case(driver, case, nodes, edges, cases)
        export_graph_json(driver, summary)
        exported_cases.append(case)
        summaries.append(summary)

    driver.close()

    if exported_cases:
        write_combined_graphs_js(case_ids)
        print(f"\nViewer data written to {VIEWER_GRAPHS_DIR}/ and {VIEWER_GRAPHS_JS}")
        print("Open viewer/index.html in your browser.")

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
    print(f"Done. Last graph built ({targets[-1]}) is live in Neo4j — "
          f"browse at http://localhost:7474")


if __name__ == "__main__":
    main()
