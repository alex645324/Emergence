"""
Parse Regulatory Timelines from Excel and produce structured JSON
with four-dimension classifications for each permitting event.
"""

import json
import re
import openpyxl

EXCEL_PATH = "data/Proof Sheet-4.xlsx"
OUTPUT_PATH = "data/events.json"

# --- Dimension classification maps ---

JURISDICTION_TYPE_MAP = {
    "city council": "municipal",
    "city of katy": "municipal",
    "katy city council": "municipal",
    "mayor": "municipal",
    "planning and zoning": "municipal",
    "commissioners court": "county_commissioner",
    "commissioners": "county_commissioner",
    "county": "county_commissioner",
    "fire marshal": "county_commissioner",
    "county engineer": "county_commissioner",
    "district court": "district_court",
    "judicial district": "district_court",
    "district attorney": "district_court",
    "puc": "state_agency",
    "puct": "state_agency",
    "public utility commission": "state_agency",
    "ercot": "state_agency",
    "soah": "state_agency",
    "representative": "federal_agency",
    "congress": "federal_agency",
    "u.s. rep": "federal_agency",
}

MECHANISM_CATEGORY_MAP = {
    "special use permit": "zoning_denial",
    "denial of special use permit": "zoning_denial",
    "zoning": "zoning_denial",
    "fire code": "fire_code_enforcement",
    "nfpa": "fire_code_enforcement",
    "fire marshal": "fire_code_enforcement",
    "health & safety code": "health_safety_litigation",
    "health and safety": "health_safety_litigation",
    "temporary restraining order": "court_injunction",
    "tro": "court_injunction",
    "injunction": "court_injunction",
    "temporary injunction": "court_injunction",
    "stop work order": "court_injunction",
    "resolution": "commissioner_resolution",
    "county resolution": "commissioner_resolution",
    "moratorium": "emergency_moratorium",
    "petition for damages": "health_safety_litigation",
    "petition in intervention": "health_safety_litigation",
    "counterclaim": "health_safety_litigation",
    "lawsuit": "health_safety_litigation",
    "appeal": "permit_denial_appeal",
    "declaratory order": "permit_denial_appeal",
    "pura": "permit_denial_appeal",
    "congressional": "legislative_action",
    "flood damage prevention": "fire_code_enforcement",
    "intervention": "permit_denial_appeal",
    "statement of interest": "permit_denial_appeal",
    "procedural schedule": "permit_denial_appeal",
    "interconnection agreement": "project_announcement",
    "project announcement": "project_announcement",
    "project proposal": "project_announcement",
    "community outreach": "public_action",
    "public meeting": "public_action",
    "public comment": "public_action",
    "commissioner's court meeting": "public_action",
    "presentation": "project_announcement",
}

# Case ID to project type
CASE_PROJECT_TYPE = {
    "van_zandt": "bess",
    "gillespie_rogers": "bess",
    "katy_ochoa": "bess",
    "gillespie_marshall": "solar_plus_storage",
}


def classify_jurisdiction_type(entity, action, mechanism):
    """Classify jurisdiction type from entity/action/mechanism text."""
    combined = f"{entity} {action} {mechanism}".lower()
    for keyword, jtype in JURISDICTION_TYPE_MAP.items():
        if keyword in combined:
            return jtype
    # Fallback: if residents/citizens are the entity
    if "resident" in combined or "citizen" in combined:
        return "citizen_action"
    return "unknown"


def classify_mechanism(mechanism_raw, action):
    """Classify legal mechanism category."""
    combined = f"{mechanism_raw} {action}".lower()
    for keyword, mcat in MECHANISM_CATEGORY_MAP.items():
        if keyword in combined:
            return mcat
    if "n/a" in combined or "announcement" in combined:
        return "project_announcement"
    return "unknown"


def determine_sequence_position(events_in_case, idx):
    """Determine sequence position based on order within case."""
    if idx == 0:
        return "project_announcement"
    mechanisms_so_far = [e["mechanism_category"] for e in events_in_case[:idx]]
    current = events_in_case[idx]["mechanism_category"]

    # First regulatory action against the project
    non_announcement = [m for m in mechanisms_so_far if m not in ("project_announcement", "public_action")]
    if not non_announcement and current not in ("project_announcement", "public_action"):
        return "first_regulatory_action"

    # Legislative/congressional response
    if current == "legislative_action":
        return "legislative_response"

    # Court response to prior action
    if current in ("court_injunction", "health_safety_litigation") and any(
        m in ("commissioner_resolution", "fire_code_enforcement", "zoning_denial")
        for m in mechanisms_so_far
    ):
        return "court_response_to_agency"

    # General escalation
    if non_announcement:
        return "escalation_same_jurisdiction"

    return "first_public_action"


def normalize_date(date_str):
    """Normalize date string to ISO-ish format with approximate flag."""
    if not date_str:
        return None, True
    date_str = str(date_str).strip()

    # Already ISO
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str, False

    # Year only
    if re.match(r"^\d{4}$", date_str):
        return f"{date_str}-01-01", True

    # Patterns like "2024-08 (exact date unknown)"
    m = re.match(r"(\d{4}-\d{2})", date_str)
    if m:
        return f"{m.group(1)}-01", True

    # Patterns like "2024 (exact date unknown)"
    m = re.match(r"(\d{4})", date_str)
    if m:
        return f"{m.group(1)}-01-01", True

    return date_str, True


def identify_case(case_header):
    """Map case header to a case_id."""
    header = case_header.lower()
    if "van zandt" in header:
        return "van_zandt"
    if "rogers draw" in header or ("gillespie" in header and "rogers" in header):
        return "gillespie_rogers"
    if "katy" in header or "ochoa" in header:
        return "katy_ochoa"
    if "marshall" in header or "ampyr" in header:
        return "gillespie_marshall"
    return "unknown"


def parse():
    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb["Regulatory Timelines"]

    all_events = []
    current_case_id = None
    current_case_events = []

    for row in ws.iter_rows(min_row=2, values_only=True):
        case_col, date_col, entity_col, action_col, mechanism_col, source_col = row[:6]

        # Case header row
        if case_col and str(case_col).startswith("---"):
            # Finalize previous case
            if current_case_events:
                for i, evt in enumerate(current_case_events):
                    evt["sequence_position"] = determine_sequence_position(current_case_events, i)
                all_events.extend(current_case_events)

            current_case_id = identify_case(str(case_col))
            current_case_events = []
            continue

        # Skip empty rows
        if not case_col and not action_col:
            continue

        date_normalized, date_approximate = normalize_date(date_col)

        event = {
            "case_id": current_case_id,
            "jurisdiction": str(case_col).strip() if case_col else current_case_id,
            "date": date_normalized,
            "date_approximate": date_approximate,
            "entity": str(entity_col).strip() if entity_col else "",
            "action_description": str(action_col).strip() if action_col else "",
            "legal_mechanism_raw": str(mechanism_col).strip() if mechanism_col else "",
            "source_url": str(source_col).strip() if source_col else "",
            "jurisdiction_type": classify_jurisdiction_type(
                str(entity_col or ""), str(action_col or ""), str(mechanism_col or "")
            ),
            "project_type": CASE_PROJECT_TYPE.get(current_case_id, "unknown"),
            "mechanism_category": classify_mechanism(
                str(mechanism_col or ""), str(action_col or "")
            ),
            "sequence_position": None,  # filled after full case is parsed
        }
        current_case_events.append(event)

    # Finalize last case
    if current_case_events:
        for i, evt in enumerate(current_case_events):
            evt["sequence_position"] = determine_sequence_position(current_case_events, i)
        all_events.extend(current_case_events)

    # Write output
    with open(OUTPUT_PATH, "w") as f:
        json.dump(all_events, f, indent=2)

    print(f"Parsed {len(all_events)} events across cases:")
    case_counts = {}
    for e in all_events:
        case_counts[e["case_id"]] = case_counts.get(e["case_id"], 0) + 1
    for cid, count in case_counts.items():
        print(f"  {cid}: {count} events")

    # Validation
    missing = [e for e in all_events if e["jurisdiction_type"] == "unknown"]
    if missing:
        print(f"\nWARNING: {len(missing)} events with unknown jurisdiction_type:")
        for m in missing:
            print(f"  - {m['date']} | {m['entity'][:50]}")

    missing_mech = [e for e in all_events if e["mechanism_category"] == "unknown"]
    if missing_mech:
        print(f"\nWARNING: {len(missing_mech)} events with unknown mechanism_category:")
        for m in missing_mech:
            print(f"  - {m['date']} | {m['legal_mechanism_raw'][:60]}")


if __name__ == "__main__":
    parse()
