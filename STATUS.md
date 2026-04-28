# PFI Graph Test — Status

## Where We Left Off

**Date:** 2026-04-27

First end-to-end run of the leave-one-out graph test against Neo4j is
complete on the expanded dataset (11 cases, 100 events). The test
produces a real signal: clean-build cases cluster in non-escalation
neighborhoods, escalation cases cluster in escalation neighborhoods,
the withdrawn case (Flat Rock) sits in escalation territory consistent
with it being killed by opposition.

## Completed

- **Step 1: Data parsing** — `scripts/parse_data.py` reads
  `data/Proof Sheet - Regulatory Timelines.csv` (Apr 27 export) and
  outputs `data/events.json` as `{events, cases}`. 100 events across
  11 cases, each classified by jurisdiction_type, project_type,
  mechanism_category, sequence_position. Per-case metadata captures
  `outcome_label`, `outcome_category`, and best-effort pre-reg
  dimensions (ERCOT queue id/date, capacity_mw, receptor_distance_ft).

  Outcome breakdown:
  - **clean (3):** Sun Valley, Anemoi, Great Kiskadee
  - **escalation (6):** Van Zandt, Rogers Draw, Katy/Ochoa, Marshall Springs, Platinum/Fannin, Black Mountain/Kerr
  - **withdrawn (1):** Flat Rock/Kendall
  - **under_construction (1):** Apache Hill/Hood

- **Step 2: Graph test built and run** — `scripts/run_test.py`
  builds a Neo4j graph for each held-out case from the *full* timelines
  of the other 10 cases plus only the **first 3 actions** of the held-out
  case. Edges weighted by an explicit 5-dim force function (no
  embeddings); edges with weight ≥ 0.5 written as `SIMILAR_TO`. Reports
  each held-out early action's top-K neighbors with their case,
  mechanism, outcome category, and sequence position. Final summary
  table sorts cases by outcome and shows escalation-% and
  clean-neighbor-% per case.

  Force function (unchanged from build):
  - `mechanism_category` (categorical match, weight 0.30)
  - `jurisdiction_type` (categorical match, weight 0.20)
  - `seq_pos_norm` (gaussian, 0.20)
  - `agency_level` (gaussian, 0.20, ordinal 0–5 from citizen → federal)
  - `elapsed_days_since_prior` (log-gaussian, 0.10)

  Escalation mechanism set (used to score neighborhoods):
  `court_injunction`, `health_safety_litigation`, `fire_code_enforcement`,
  `zoning_denial`, `permit_denial_appeal`, `emergency_moratorium`,
  `commissioner_resolution`. Adding `commissioner_resolution` was the
  one tuning change after the first run — county resolutions opposing a
  project are explicit county-level escalation actions; the original
  set was missing them.

## First Run Results (2026-04-27)

Sorted by outcome, then by escalation-% descending:

| case_id              | outcome            | esc% | clean-neigh% | neighbors |
|----------------------|--------------------|-----:|-------------:|----------:|
| hidalgo_kiskadee     | clean              |  33% |          33% | 15        |
| hidalgo_anemoi       | clean              |  13% |          53% | 15        |
| hill_sun_valley      | clean              |   6% |          66% | 15        |
| hood_apache_hill     | under_construction |  13% |          66% | 15        |
| kendall_flat_rock    | withdrawn          |  40% |          13% | 15        |
| gillespie_rogers     | escalation         |  93% |           0% | 15        |
| kerr_black_mountain  | escalation         |  60% |          20% | 15        |
| van_zandt            | escalation         |  46% |          26% | 15        |
| gillespie_marshall   | escalation         |  40% |          33% | 15        |
| fannin_platinum      | escalation         |  20% |          33% | 15        |
| katy_ochoa           | escalation         |   0% |           0% | 6         |

### Read of the results

- **Clean cases land where they should.** Sun Valley (6% esc, 66%
  clean), Anemoi (13%, 53%), Apache Hill — under_construction but
  pre-opposition — (13%, 66%). The early actions of clean projects
  (ERCOT interconnection, tax abatement, financing milestones) match
  similar non-escalation actions in other clean projects.
- **Withdrawn (Flat Rock) sits in escalation territory.** 40% esc, 13%
  clean. Consistent with the case: it was killed by opposition (county
  IFC adoption + 391 commission + sustained pushback) and its early
  actions land near other early opposition actions, not near clean
  builds.
- **Most escalation cases score high.** Rogers Draw 93%, Black Mountain
  60%, Van Zandt 46%, Marshall Springs 40%. Their early actions are
  dominated by mechanisms that recur across other escalation cases
  (commissioner_resolution, fire_code_enforcement, court_injunction).

### Two interpretable misses

- **Kiskadee at 33% esc is high for a clean case.** Worth inspecting
  in the live graph — likely a single early Kiskadee action lands near
  an `interconnection_agreement` event that happens to be co-located in
  a case with later opposition (ERCOT processes are common to clean and
  escalating projects alike). Not a parser bug; the force function is
  using a real similarity. Candidate fix: down-weight edges to events
  whose *case* is opposite-outcome (would require leaking the outcome
  label, defeating the test purpose) — better fix is probably to add
  more pre-reg dimensions (capacity, receptor distance, queue date)
  so non-regulatory features pull cases apart.
- **Platinum at 20%.** Project was acquired in 2022; opposition started
  2025. With early window = 3, Platinum's first 3 actions
  (commercial_milestone, public_action, legislative_action) precede the
  fire-marshal pushback — by design, the test gets the early window
  before regulatory action. This is a real limitation of the
  early-window framing for projects with long lead times, not a
  classifier failure.
- **Katy at 0% (only 6 neighbors).** Katy is the only case with
  `zoning_denial` in the dataset, so its early actions can't match by
  mechanism. Most candidate edges fall below the 0.5 threshold. Reflects
  data sparsity — would need another zoning-denial case to test against.

## Next Steps

Open questions worth a deliberate decision before another iteration:

1. **Add pre-reg dimensions to the force function?** We have ERCOT
   queue date, capacity_mw, and receptor_distance_ft on (most) cases.
   Adding capacity and queue-date as additional gaussian dimensions
   would help separate cases that are similar regulatorily but
   different in size or queue vintage.
2. **Lower the edge threshold for sparse cases (Katy)?** Or add more
   zoning-denial cases.
3. **Vary the early window** (3 → 5 → 7) to see how the signal
   degrades for projects whose opposition arrives years later
   (Platinum, Apache Hill).
4. **Backfill missing pre-reg rows** — Sun Valley (case 5), Anemoi
   (case 6), Black Mountain (case 10), Flat Rock (case 8 — has a row
   but the queue ID is "NOT FOUND") have no parsed `ercot_queue_id`.
   Useful before option (1).

## Files

- `data/Proof Sheet - Regulatory Timelines.csv` — source of truth for
  events, outcomes, and pre-reg dimensions (Apr 27 export)
- `data/events.json` — parser output, `{events: [...], cases: {...}}`
- `scripts/parse_data.py` — CSV → events.json
- `scripts/run_test.py` — leave-one-out graph test against Neo4j
- `docker-compose.yml` — Neo4j container config (unused on this
  machine; Neo4j installed via `brew install neo4j` instead)
- `requirements.txt` — `neo4j`, `openpyxl` (openpyxl no longer used by
  the parser but kept for re-export utilities)

## How to run

```
brew services start neo4j     # one-time on this machine
.venv/bin/python scripts/parse_data.py
.venv/bin/python scripts/run_test.py            # all 11 cases
.venv/bin/python scripts/run_test.py --case van_zandt   # one case, browse at :7474
```

Neo4j auth: `neo4j` / `pfi_graph_test` (set on first run via
`ALTER CURRENT USER SET PASSWORD`).
