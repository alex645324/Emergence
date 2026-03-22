# PFI Graph Test — Status

## Where We Left Off

**Date:** 2026-03-22

## Completed

- **Step 1: Data parsing** — `scripts/parse_data.py` parses the Regulatory Timelines sheet from `data/Proof Sheet-4.xlsx` and outputs `data/events.json` with 36 events across 4 cases, each classified across four dimensions (jurisdiction_type, project_type, mechanism_category, sequence_position).

### Cases in dataset
| Case | Events | Project Type |
|------|--------|-------------|
| Van Zandt County | 9 | BESS |
| Gillespie County — Rogers Draw | 8 | BESS |
| Katy — Ochoa | 9 | BESS |
| Gillespie County — Marshall Springs | 10 | Solar + Storage |

## Next Up: Step 2

Build the full test pipeline. Approved plan:

1. **Docker Compose** for Neo4j
2. **`scripts/run_test.py`** that for each of the 4 cases:
   - Clears the graph
   - Loads all events from the other 3 cases (full timelines)
   - Loads only the **first regulatory action** from the test case (the rewind point)
   - Generates embeddings (sentence-transformers, action description + four dimensions)
   - Computes pairwise cosine similarity, creates `SIMILAR_TO` edges above threshold
   - Queries the graph: what does the early action connect to? Do those connections point toward escalation?
3. **Output:** 4 reports, one per case. We read them and judge pass/fail.

### Rewind points per case
- **Van Zandt:** December 2024 resident lawsuit (Cause No. 24-00204)
- **Gillespie Rogers:** February 2025 commissioner resolution opposing BESS
- **Katy Ochoa:** October 2024 City Council SUP denial
- **Gillespie Marshall:** November 2025 commissioner resolution opposing solar/BESS

### Dependencies to install
- `neo4j` (Python driver)
- `sentence-transformers`
- `numpy`

### Key design constraint
No human-defined queries. Feed the early action, read what the graph expresses. The structure either shows the early action sitting near other early actions that preceded escalation, or it doesn't. That is the test.
