"""Check the denial-case set: cases/cases.csv against the page text and the letters.

Stdlib only. Run from anywhere:  python cases/verify.py

Per row:
  - enums are valid (program and member_age_group use the case card enums in policyqa/intake.py)
  - dates are ISO (YYYY-MM-DD; dates_of_service may be a range START/END)
  - the hinge quote appears in data/text/<hinge_doc_id>/p<NNN>.txt, whitespace normalized.
    A row whose document folder is missing on this machine is "unverifiable here", not a failure.
  - the letter exists, is 600 to 1,500 characters, starts with the sample line, ends with a synthetic line
  - the letter states the amount, the dates of service, the letter date, the denial reason, the service
    code when set, and the appeal deadline when set
Whole set:
  - 30 rows, ids unique; outcome mix 14 / 10 / 6; 4 traps; 10 demo rows with at least
    5 inconsistent, 3 consistent, 2 not_settled, and 1 trap

Exit code 0 when no row fails, 1 otherwise.
"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
TEXT = REPO / "data" / "text"
CSV_PATH = HERE / "cases.csv"
LETTERS = HERE / "letters"

COLUMNS = [
    "id", "program", "member_age_group", "jurisdiction", "service", "service_code", "denial_reason",
    "intended_outcome", "hinge_doc_id", "hinge_page", "hinge_quote", "amount_billed", "dates_of_service",
    "letter_date", "appeal_deadline_claimed", "difficulty", "trap", "demo", "notes", "payer_name",
]
# Same values as PROGRAMS and AGE_GROUPS in policyqa/intake.py (kept here so this script stays stdlib only).
PROGRAMS = {"florida_medicaid_mma", "florida_medicaid_ltc", "florida_kidcare", "medicare_a", "medicare_b",
            "medicare_advantage", "medicare_part_d", "unknown"}
AGE_GROUPS = {"under_21", "adult", "65_plus", "unknown"}
JURISDICTIONS = {"Florida", "Federal", "both"}
OUTCOMES = {"consistent", "inconsistent", "not_settled"}
DIFFICULTIES = {"easy", "medium", "hard"}
YES_NO = {"yes", "no"}

FIRST_LINE = "SAMPLE LETTER FOR DEMONSTRATION. NOT A REAL NOTICE."
LETTER_MIN, LETTER_MAX = 600, 1500
TARGET_OUTCOMES = {"inconsistent": 14, "consistent": 10, "not_settled": 6}
TARGET_ROWS, TARGET_TRAPS, TARGET_DEMO = 30, 4, 10
DEMO_MIN = {"inconsistent": 5, "consistent": 3, "not_settled": 2}


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def iso(s: str) -> date | None:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def words(d: date) -> str:
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def check_row(r: dict) -> tuple[list[str], bool]:
    """Return (problems, unverifiable_here)."""
    p: list[str] = []
    for field, allowed in (("program", PROGRAMS), ("member_age_group", AGE_GROUPS), ("jurisdiction", JURISDICTIONS),
                           ("intended_outcome", OUTCOMES), ("difficulty", DIFFICULTIES), ("trap", YES_NO), ("demo", YES_NO)):
        if r[field] not in allowed:
            p.append(f"{field} not in enum: {r[field]!r}")
    for field in ("service", "denial_reason", "hinge_doc_id", "hinge_quote", "notes", "payer_name"):
        if not r[field].strip():
            p.append(f"{field} is empty")

    # dates
    letter_date = iso(r["letter_date"])
    if letter_date is None:
        p.append(f"letter_date not ISO: {r['letter_date']!r}")
    dos_parts = r["dates_of_service"].split("/")
    dos = [iso(x) for x in dos_parts]
    if not (1 <= len(dos) <= 2) or any(d is None for d in dos) or (len(dos) == 2 and dos[0] > dos[1]):
        p.append(f"dates_of_service not a valid date or range: {r['dates_of_service']!r}")
        dos = []
    deadline = None
    if r["appeal_deadline_claimed"]:
        deadline = iso(r["appeal_deadline_claimed"])
        if deadline is None:
            p.append(f"appeal_deadline_claimed not ISO: {r['appeal_deadline_claimed']!r}")
        elif letter_date and deadline <= letter_date:
            p.append("appeal deadline is not after the letter date")
    amount = None
    if r["amount_billed"]:
        try:
            amount = float(r["amount_billed"])
            if not 0 <= amount < 100_000:
                p.append("amount_billed out of range")
        except ValueError:
            p.append(f"amount_billed not a number: {r['amount_billed']!r}")

    # hinge quote against the page text
    unverifiable = False
    try:
        page = int(r["hinge_page"])
    except ValueError:
        page = -1
        p.append(f"hinge_page not an integer: {r['hinge_page']!r}")
    doc_dir = TEXT / r["hinge_doc_id"]
    if not doc_dir.is_dir():
        unverifiable = True
    elif page >= 1:
        page_file = doc_dir / f"p{page:03d}.txt"
        if not page_file.is_file():
            p.append(f"page file missing: {page_file.relative_to(REPO)}")
        elif norm(r["hinge_quote"]) not in norm(page_file.read_text(encoding="utf-8")):
            p.append(f"hinge quote not found in {page_file.relative_to(REPO)}")

    # letter
    letter_path = LETTERS / f"{r['id']}.txt"
    if not letter_path.is_file():
        p.append(f"letter missing: {letter_path.relative_to(REPO)}")
        return p, unverifiable
    letter = letter_path.read_text(encoding="utf-8")
    body = letter.strip()
    if not LETTER_MIN <= len(body) <= LETTER_MAX:
        p.append(f"letter length {len(body)} outside {LETTER_MIN} to {LETTER_MAX}")
    lines = [ln for ln in body.splitlines() if ln.strip()]
    if not lines or lines[0].strip() != FIRST_LINE:
        p.append("letter first line is not the sample line")
    if not lines or "synthetic" not in lines[-1].lower():
        p.append("letter last line does not say it is synthetic")
    flat = norm(letter)
    if amount is not None and f"${amount:,.2f}" not in flat:
        p.append(f"letter does not state the amount ${amount:,.2f}")
    for d in dos:
        if words(d) not in flat:
            p.append(f"letter does not state the date of service {words(d)}")
    if letter_date and words(letter_date) not in flat:
        p.append(f"letter does not state the letter date {words(letter_date)}")
    if deadline and words(deadline) not in flat:
        p.append(f"letter does not state the deadline {words(deadline)}")
    if norm(r["denial_reason"]) not in flat:
        p.append("letter does not contain the denial reason verbatim")
    if r["service_code"] and r["service_code"] not in flat:
        p.append(f"letter does not state the service code {r['service_code']}")
    return p, unverifiable


def check_set(rows: list[dict]) -> list[str]:
    p: list[str] = []
    ids = [r["id"] for r in rows]
    if len(rows) != TARGET_ROWS:
        p.append(f"{len(rows)} rows, expected {TARGET_ROWS}")
    if len(set(ids)) != len(ids):
        p.append("duplicate ids")
    bad_ids = [i for i in ids if not re.fullmatch(r"dc-\d{3}", i)]
    if bad_ids:
        p.append(f"ids not in dc-NNN form: {bad_ids}")
    outcomes = Counter(r["intended_outcome"] for r in rows)
    if dict(outcomes) != TARGET_OUTCOMES:
        p.append(f"outcome mix {dict(outcomes)}, expected {TARGET_OUTCOMES}")
    traps = sum(r["trap"] == "yes" for r in rows)
    if traps != TARGET_TRAPS:
        p.append(f"{traps} traps, expected {TARGET_TRAPS}")
    demo = [r for r in rows if r["demo"] == "yes"]
    if len(demo) != TARGET_DEMO:
        p.append(f"{len(demo)} demo rows, expected {TARGET_DEMO}")
    demo_outcomes = Counter(r["intended_outcome"] for r in demo)
    for k, n in DEMO_MIN.items():
        if demo_outcomes[k] < n:
            p.append(f"demo has {demo_outcomes[k]} {k}, expected at least {n}")
    if not any(r["trap"] == "yes" for r in demo):
        p.append("no trap among the demo rows")
    extra = set(LETTERS.glob("*.txt")) - {LETTERS / f"{i}.txt" for i in ids}
    if extra:
        p.append(f"letters with no row: {sorted(x.name for x in extra)}")
    return p


def main() -> int:
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing_cols = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing_cols:
            print(f"FAIL header: missing columns {missing_cols}")
            return 1
        rows = list(reader)

    verified, unverifiable, failed = [], [], []
    for r in rows:
        problems, unver = check_row(r)
        if problems:
            failed.append(r["id"])
            for msg in problems:
                print(f"FAIL {r['id']}: {msg}")
        elif unver:
            unverifiable.append(r["id"])
            print(f"UNVERIFIABLE HERE {r['id']}: no page text for {r['hinge_doc_id']} on this machine")
        else:
            verified.append(r["id"])

    set_problems = check_set(rows)
    for msg in set_problems:
        print(f"FAIL set: {msg}")

    print()
    print(f"rows: {len(rows)}")
    print(f"verified: {len(verified)}")
    print(f"unverifiable here: {len(unverifiable)}")
    print(f"failures: {len(failed)}" + (f" ({', '.join(failed)})" if failed else ""))
    print(f"set checks: {'pass' if not set_problems else 'FAIL'}")
    print("outcomes:", dict(Counter(r["intended_outcome"] for r in rows)))
    print("programs:", dict(Counter(r["program"] for r in rows)))
    print("demo:", sum(r["demo"] == "yes" for r in rows), "| traps:", sum(r["trap"] == "yes" for r in rows))
    return 1 if failed or set_problems else 0


if __name__ == "__main__":
    sys.exit(main())
