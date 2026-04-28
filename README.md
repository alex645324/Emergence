# PFI Graph Test

A position-system prototype for permitting data. Drop the early actions
of an unseen project into a graph built from other projects, and the
neighborhood the actions land in tells you what's likely to happen —
without ever telling the system the outcome.

Tested on 11 Texas BESS (battery storage) projects with 100 regulatory
events. The held-out case lands in its predicted territory in 8 of 11
cases. The 3 misses are interpretable, not bugs.

## Demo

```
open viewer/index.html
```

Pick a held-out case from the dropdown. The 10 other cases settle into
their natural clusters. Click **inject case** and watch the 3 hidden
events drift to where they belong. The card top-right reads the result.

## Re-run the test from raw data

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/parse_data.py
python scripts/run_test.py
open viewer/index.html
```

No database. No server.

## What is where

- `Data/Proof Sheet - Regulatory Timelines.csv` — the 100 hand-curated events
- `Data/events.json` — parsed + classified events
- `scripts/parse_data.py` — CSV → events.json
- `scripts/run_test.py` — runs the leave-one-out test, writes the viewer data
- `viewer/index.html` — the visual demo (D3 force layout)
- `viewer/graphs.js` — pre-baked test results so the demo runs without re-running

## What to look at first

1. **`viewer/index.html`** in a browser — this is the point.
2. **`scripts/run_test.py`** if you want to read how the test works.
3. **`scripts/parse_data.py`** if you want to read how the data is classified.
