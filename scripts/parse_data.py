"""
Parse Regulatory Timelines CSV and produce structured JSON
with four-dimension classifications for each permitting event,
plus per-case outcome and pre-reg metadata.
"""

import csv
import json
import re
from datetime import datetime, timedelta

CSV_PATH = "data/Proof Sheet - Regulatory Timelines.csv"
OUTPUT_PATH = "data/events.json"

CASE_NUMBER_TO_ID = {
    1: "van_zandt",
    2: "gillespie_rogers",
    3: "katy_ochoa",
    4: "gillespie_marshall",
    5: "hill_sun_valley",
    6: "hidalgo_anemoi",
    7: "hidalgo_kiskadee",
    8: "kendall_flat_rock",
    9: "fannin_platinum",
    10: "kerr_black_mountain",
    11: "hood_apache_hill",
}

CASE_PROJECT_TYPE = {
    "van_zandt": "bess",
    "gillespie_rogers": "bess",
    "katy_ochoa": "bess",
    "gillespie_marshall": "solar_plus_storage",
    "hill_sun_valley": "solar_plus_storage",
    "hidalgo_anemoi": "bess",
    "hidalgo_kiskadee": "bess",
    "kendall_flat_rock": "bess",
    "fannin_platinum": "bess",
    "kerr_black_mountain": "bess",
    "hood_apache_hill": "bess",
}

# Substring (lowercase) -> case_id, used when current_case_id is unset
# (rows in OUTCOME LABELS & UPDATES section name the case in column 0).
JURISDICTION_TO_CASE_ID = [
    ("van zandt", "van_zandt"),
    ("rogers draw", "gillespie_rogers"),
    ("marshall springs", "gillespie_marshall"),
    ("ochoa", "katy_ochoa"),
    ("katy", "katy_ochoa"),
    ("sun valley", "hill_sun_valley"),
    ("anemoi", "hidalgo_anemoi"),
    ("great kiskadee", "hidalgo_kiskadee"),
    ("flat rock", "kendall_flat_rock"),
    ("platinum bess", "fannin_platinum"),
    ("platinum", "fannin_platinum"),
    ("black mountain", "kerr_black_mountain"),
    ("apache hill", "hood_apache_hill"),
]

# Outcome category extraction (substring match on lowercased description).
# Order matters: most specific first.
OUTCOME_PATTERNS = [
    ("delayed_in_litigation", "escalation"),
    ("ongoing_dispute", "escalation"),
    ("withdrawn", "withdrawn"),
    ("under_construction", "under_construction"),
    ("outcome: built", "clean"),
    ("built —", "clean"),
]

# Ordered list-of-tuples: more specific keywords first.
JURISDICTION_TYPE_MAP = [
    ("city of katy", "municipal"),
    ("katy city council", "municipal"),
    ("city council", "municipal"),
    ("councilmember", "municipal"),
    ("planning and zoning", "municipal"),
    ("mayor", "municipal"),
    ("hidalgo county planning", "county_commissioner"),
    ("county planning department", "county_commissioner"),
    ("commissioners court", "county_commissioner"),
    ("commissioner court", "county_commissioner"),
    ("county commissioner", "county_commissioner"),
    ("county engineer", "county_commissioner"),
    ("county judge", "county_commissioner"),
    ("county attorney", "county_commissioner"),
    ("county officials", "county_commissioner"),
    ("fire marshal", "county_commissioner"),
    ("kerr county", "county_commissioner"),
    ("kendall county", "county_commissioner"),
    ("fannin county", "county_commissioner"),
    ("hood county", "county_commissioner"),
    ("hill county", "county_commissioner"),
    ("hidalgo county", "county_commissioner"),
    ("gillespie county", "county_commissioner"),
    ("van zandt county", "county_commissioner"),
    ("delta county", "county_commissioner"),
    ("district court", "district_court"),
    ("district court judge", "district_court"),
    ("judicial district", "district_court"),
    ("district judge", "district_court"),
    ("district attorney", "district_court"),
    ("texas attorney general", "state_agency"),
    ("attorney general", "state_agency"),
    ("public utility commission", "state_agency"),
    ("puct", "state_agency"),
    ("puc", "state_agency"),
    ("soah", "state_agency"),
    ("tceq", "state_agency"),
    ("lcra", "state_agency"),
    ("ercot", "state_agency"),
    ("texas legislature", "state_agency"),
    ("texas senator", "state_agency"),
    ("texas representative", "state_agency"),
    ("rep. ellen troxclair", "state_agency"),
    ("state rep", "state_agency"),
    ("texas state", "state_agency"),
    ("ferc", "federal_agency"),
    ("nadbank", "federal_agency"),
    ("u.s. rep", "federal_agency"),
    ("u.s. senator", "federal_agency"),
    ("rep. chip roy", "federal_agency"),
    ("representative chip roy", "federal_agency"),
    ("congress", "federal_agency"),
]

# Ordered list-of-tuples: most specific first.
MECHANISM_CATEGORY_MAP = [
    ("agreed temporary injunction", "court_injunction"),
    ("temporary restraining order", "court_injunction"),
    ("temporary injunction", "court_injunction"),
    ("stop work order", "court_injunction"),
    ("tro", "court_injunction"),
    ("injunction", "court_injunction"),
    ("denial of special use permit", "zoning_denial"),
    ("special use permit", "zoning_denial"),
    ("zoning", "zoning_denial"),
    ("petition in intervention", "health_safety_litigation"),
    ("petition for damages", "health_safety_litigation"),
    ("counterclaim", "health_safety_litigation"),
    ("civil action", "health_safety_litigation"),
    ("lawsuit", "health_safety_litigation"),
    ("rule 91a", "permit_denial_appeal"),
    ("declaratory order", "permit_denial_appeal"),
    ("answer to counterclaims", "permit_denial_appeal"),
    ("statement of interest", "permit_denial_appeal"),
    ("attorney general opinion", "permit_denial_appeal"),
    ("motion to dismiss", "permit_denial_appeal"),
    ("procedural schedule", "permit_denial_appeal"),
    ("intervention", "permit_denial_appeal"),
    ("appeal", "permit_denial_appeal"),
    ("pura", "permit_denial_appeal"),
    ("tort", "permit_denial_appeal"),
    ("emergency moratorium", "emergency_moratorium"),
    ("moratorium", "emergency_moratorium"),
    ("nfpa", "fire_code_enforcement"),
    ("international fire code", "fire_code_enforcement"),
    ("fire code", "fire_code_enforcement"),
    ("flood damage prevention", "fire_code_enforcement"),
    ("fire marshal", "fire_code_enforcement"),
    ("health & safety code", "health_safety_litigation"),
    ("health and safety", "health_safety_litigation"),
    ("tax abatement denial", "commissioner_resolution"),
    ("tax abatement guidelines", "tax_abatement_agreement"),
    ("tax abatement agreement", "tax_abatement_agreement"),
    ("tax abatement", "tax_abatement_agreement"),
    ("county resolution opposing", "commissioner_resolution"),
    ("resolution opposing", "commissioner_resolution"),
    ("county resolution", "commissioner_resolution"),
    ("sub-regional planning", "commissioner_resolution"),
    ("391 commission", "commissioner_resolution"),
    ("chapter 391", "commissioner_resolution"),
    ("resolution", "commissioner_resolution"),
    ("congressional inquiry", "legislative_action"),
    ("congressional follow-up", "legislative_action"),
    ("congressional", "legislative_action"),
    ("political declaration", "legislative_action"),
    ("press statement", "legislative_action"),
    ("press release", "legislative_action"),
    ("legislative advocacy", "legislative_action"),
    ("texas legislature", "legislative_action"),
    ("state bills", "legislative_action"),
    ("ercot standard generation", "interconnection_agreement"),
    ("ercot generation interconnection", "interconnection_agreement"),
    ("ercot interconnection", "interconnection_agreement"),
    ("ercot commercial operation", "commercial_operation"),
    ("interconnection agreement", "interconnection_agreement"),
    ("sgia", "interconnection_agreement"),
    ("interconnectability study", "interconnection_agreement"),
    ("puhca", "permit_issuance"),
    ("ewg", "permit_issuance"),
    ("exempt wholesale generator", "permit_issuance"),
    ("construction general permit", "permit_issuance"),
    ("stormwater authorization", "permit_issuance"),
    ("building permit", "permit_issuance"),
    ("permit application", "permit_issuance"),
    ("ppa", "commercial_milestone"),
    ("vppa", "commercial_milestone"),
    ("power purchase agreement", "commercial_milestone"),
    ("commercial offtake", "commercial_milestone"),
    ("epc contract", "commercial_milestone"),
    ("epc milestones", "construction_milestone"),
    ("project finance close", "commercial_milestone"),
    ("project finance facility", "commercial_milestone"),
    ("project finance", "commercial_milestone"),
    ("real property purchase option", "commercial_milestone"),
    ("real property purchase", "commercial_milestone"),
    ("purchase option", "commercial_milestone"),
    ("joint venture", "commercial_milestone"),
    ("project acquisition", "commercial_milestone"),
    ("portfolio transfer", "commercial_milestone"),
    ("commercial transfer", "commercial_milestone"),
    ("phase i environmental", "commercial_milestone"),
    ("phase i", "commercial_milestone"),
    ("epc", "commercial_milestone"),
    ("project advancement", "construction_milestone"),
    ("construction commencement", "construction_milestone"),
    ("county bess safety ordinance", "fire_code_enforcement"),
    ("bess safety ordinance", "fire_code_enforcement"),
    ("nadbank certification", "commercial_milestone"),
    ("nadbank board document", "commercial_milestone"),
    ("loan financing", "commercial_milestone"),
    ("project certification", "commercial_milestone"),
    ("commissioner's court presentation", "project_announcement"),
    ("commissioner court presentation", "project_announcement"),
    ("commercial operation", "commercial_operation"),
    ("project announcement", "project_announcement"),
    ("project initiation", "project_announcement"),
    ("project proposal", "project_announcement"),
    ("pre-application engagement", "project_announcement"),
    ("public meeting", "public_action"),
    ("public comment", "public_action"),
    ("community opposition", "public_action"),
    ("community outreach", "public_action"),
    ("citizen-organized", "public_action"),
    ("informational meeting", "public_action"),
    ("commissioner's court meeting", "public_action"),
    ("commissioner court meeting", "public_action"),
    ("fire marshal enforcement demand", "public_action"),
]

EXCEL_EPOCH = datetime(1899, 12, 30)


def excel_serial_to_iso(serial):
    """Convert an Excel date serial integer to ISO date string."""
    try:
        n = int(float(serial))
    except (TypeError, ValueError):
        return None
    return (EXCEL_EPOCH + timedelta(days=n)).strftime("%Y-%m-%d")


def normalize_date(date_str):
    """Normalize date string to ISO format. Returns (iso, approximate)."""
    if date_str is None:
        return None, True
    s = str(date_str).strip()
    if not s:
        return None, True

    # Excel serial number (e.g. "45689")
    if re.match(r"^\d{4,6}(\.0+)?$", s) and not re.match(r"^\d{4}$", s):
        iso = excel_serial_to_iso(s)
        if iso:
            return iso, False

    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s, False
    if re.match(r"^\d{4}-\d{2}", s):
        m = re.match(r"(\d{4}-\d{2})", s)
        return f"{m.group(1)}-01", True
    if re.match(r"^\d{4}", s):
        m = re.match(r"(\d{4})", s)
        return f"{m.group(1)}-01-01", True
    return s, True


def classify_jurisdiction_type(entity, action, mechanism):
    combined = f"{entity} {action} {mechanism}".lower()
    for keyword, jtype in JURISDICTION_TYPE_MAP:
        if keyword in combined:
            return jtype
    if any(k in combined for k in ("resident", "citizen", "homeowner", "rancher")):
        return "citizen_action"
    return "developer"


def classify_mechanism(mechanism_raw, action):
    # Mechanism column is the authoritative classifier when it explicitly
    # names a category — only fall back to the action text when it doesn't.
    mech_lower = (mechanism_raw or "").lower()
    for keyword, mcat in MECHANISM_CATEGORY_MAP:
        if keyword in mech_lower:
            return mcat
    combined = f"{mechanism_raw} {action}".lower()
    for keyword, mcat in MECHANISM_CATEGORY_MAP:
        if keyword in combined:
            return mcat
    if "n/a" in combined or "announcement" in combined:
        return "project_announcement"
    return "unknown"


def determine_sequence_position(events_in_case, idx):
    if idx == 0:
        return "project_announcement"
    mechanisms_so_far = [e["mechanism_category"] for e in events_in_case[:idx]]
    current = events_in_case[idx]["mechanism_category"]

    non_neutral = [
        m for m in mechanisms_so_far
        if m not in (
            "project_announcement", "public_action",
            "interconnection_agreement", "permit_issuance",
            "commercial_milestone", "construction_milestone",
            "commercial_operation", "tax_abatement_agreement",
        )
    ]
    if not non_neutral and current not in (
        "project_announcement", "public_action",
        "interconnection_agreement", "permit_issuance",
        "commercial_milestone", "construction_milestone",
        "commercial_operation", "tax_abatement_agreement",
    ):
        return "first_regulatory_action"

    if current == "legislative_action":
        return "legislative_response"

    if current in ("court_injunction", "health_safety_litigation") and any(
        m in ("commissioner_resolution", "fire_code_enforcement", "zoning_denial")
        for m in mechanisms_so_far
    ):
        return "court_response_to_agency"

    if non_neutral:
        return "escalation_same_jurisdiction"

    return "first_public_action"


def categorize_outcome(description):
    s = (description or "").lower()
    for keyword, cat in OUTCOME_PATTERNS:
        if keyword in s:
            return cat
    return "unknown"


def parse_pre_reg(description):
    """Best-effort regex extraction of pre-reg dimensions."""
    s = description or ""
    out = {}
    m = re.search(r"ERCOT[- ](\d{2}INR\d{4})", s)
    if m:
        out["ercot_queue_id"] = m.group(1)
    m = re.search(r"[Qq]ueue (?:request )?date[:\s]+(\d{4}-\d{2}-\d{2})", s)
    if m:
        out["ercot_queue_date"] = m.group(1)
    else:
        m = re.search(r"queued\s+\w+\s+(\d{4})", s, re.IGNORECASE)
        if m:
            out["ercot_queue_date"] = f"{m.group(1)}-01-01"
    m = re.search(r"(\d{2,4})(?:\.\d+)?\s*MW(?:\s*/\s*(\d{2,4})\s*MWh)?", s)
    if m:
        try:
            out["capacity_mw"] = int(m.group(1))
        except ValueError:
            pass
    m = re.search(r"~?([\d,]+)\s*ft\s+to", s)
    if m:
        try:
            out["receptor_distance_ft"] = int(m.group(1).replace(",", ""))
        except ValueError:
            pass
    return out


def is_section_divider(text):
    """Section dividers are --- ... --- rows that are not case headers."""
    return bool(re.match(r"^\s*-{3}.*-{3}\s*$", text or "")) and not re.search(
        r"CASE\s+\d+\s*:", text or "", re.IGNORECASE
    )


def case_id_from_jurisdiction(jurisdiction):
    s = (jurisdiction or "").lower()
    for keyword, cid in JURISDICTION_TO_CASE_ID:
        if keyword in s:
            return cid
    return None


def make_event(case_id, row, idx_in_case=None):
    case_col, date_col, entity_col, action_col, mechanism_col, source_col = row[:6]
    date_normalized, date_approximate = normalize_date(date_col)
    entity = (entity_col or "").strip()
    action = (action_col or "").strip()
    mechanism = (mechanism_col or "").strip()
    return {
        "case_id": case_id,
        "jurisdiction": (case_col or case_id).strip(),
        "date": date_normalized,
        "date_approximate": date_approximate,
        "entity": entity,
        "action_description": action,
        "legal_mechanism_raw": mechanism,
        "source_url": (source_col or "").strip(),
        "jurisdiction_type": classify_jurisdiction_type(entity, action, mechanism),
        "project_type": CASE_PROJECT_TYPE.get(case_id, "unknown"),
        "mechanism_category": classify_mechanism(mechanism, action),
        "sequence_position": None,
    }


def parse():
    cases = {
        cid: {
            "case_id": cid,
            "case_number": num,
            "project_type": CASE_PROJECT_TYPE.get(cid, "unknown"),
            "outcome_label": None,
            "outcome_category": None,
            "outcome_source_url": None,
            "ercot_queue_id": None,
            "ercot_queue_date": None,
            "capacity_mw": None,
            "receptor_distance_ft": None,
        }
        for num, cid in CASE_NUMBER_TO_ID.items()
    }

    events_by_case = {cid: [] for cid in CASE_NUMBER_TO_ID.values()}
    current_case_id = None

    with open(CSV_PATH, newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if not row or all(not (c or "").strip() for c in row):
                continue
            row = (row + [""] * 6)[:6]
            case_col = (row[0] or "").strip()
            date_col = (row[1] or "").strip()

            # Case header: --- CASE N: ... ---
            m = re.match(r"^\s*-{3}\s*CASE\s+(\d+)\s*:", case_col, re.IGNORECASE)
            if m:
                num = int(m.group(1))
                current_case_id = CASE_NUMBER_TO_ID.get(num)
                continue

            # Other --- ... --- dividers
            if is_section_divider(case_col):
                current_case_id = None
                continue

            # Determine which case this row belongs to. Prefer the case named
            # in column 0 — OUTCOME / PRE-REG / Case-N-update rows live in
            # summary blocks where current_case_id from the last "--- CASE N ---"
            # header refers to a different case. Fall back to current_case_id
            # only when the jurisdiction string doesn't identify a case.
            row_case_id = case_id_from_jurisdiction(case_col) or current_case_id
            if not row_case_id:
                continue

            # Skip rows that are not actual cases (INVESTIGATED candidates)
            if date_col.upper().startswith("INVESTIGATED"):
                continue

            # OUTCOME / OUTCOME LABEL row
            if date_col.upper() in ("OUTCOME", "OUTCOME LABEL"):
                desc = (row[3] or "").strip()
                cases[row_case_id]["outcome_label"] = desc
                cases[row_case_id]["outcome_category"] = categorize_outcome(desc)
                cases[row_case_id]["outcome_source_url"] = (row[5] or "").strip()
                continue

            # PRE-REG DIMENSIONS row
            if date_col.upper().startswith("PRE-REG DIMENSIONS"):
                desc = (row[3] or "").strip()
                cases[row_case_id].update(parse_pre_reg(desc))
                continue

            # Otherwise, it's an event — but skip summary rows that lack a date
            # (e.g. "REJECTED — ..." disqualifier-summary rows mid-sheet).
            if not date_col:
                continue
            events_by_case[row_case_id].append(make_event(row_case_id, row))

    # Sort each case's events by date and assign sequence_position
    all_events = []
    for cid, evts in events_by_case.items():
        evts.sort(key=lambda e: e["date"] or "9999-99-99")
        for i, e in enumerate(evts):
            e["sequence_position"] = determine_sequence_position(evts, i)
        all_events.extend(evts)

    output = {"events": all_events, "cases": cases}
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    # --- Summary ---
    print(f"Parsed {len(all_events)} events across {sum(1 for evts in events_by_case.values() if evts)} cases:")
    for cid, evts in events_by_case.items():
        c = cases[cid]
        print(f"  {cid:24s}  {len(evts):3d} events  outcome={c['outcome_category'] or '?':<20s} ercot={c.get('ercot_queue_id') or '?'}")

    missing_juris = [e for e in all_events if e["jurisdiction_type"] == "unknown"]
    if missing_juris:
        print(f"\nWARNING: {len(missing_juris)} events with unknown jurisdiction_type:")
        for m in missing_juris[:10]:
            print(f"  - {m['case_id']} {m['date']} | {m['entity'][:60]}")

    missing_mech = [e for e in all_events if e["mechanism_category"] == "unknown"]
    if missing_mech:
        print(f"\nWARNING: {len(missing_mech)} events with unknown mechanism_category:")
        for m in missing_mech[:10]:
            print(f"  - {m['case_id']} {m['date']} | {m['legal_mechanism_raw'][:80]}")

    missing_outcome = [cid for cid, c in cases.items() if not c["outcome_category"]]
    if missing_outcome:
        print(f"\nWARNING: {len(missing_outcome)} cases without outcome_category: {missing_outcome}")


if __name__ == "__main__":
    parse()
