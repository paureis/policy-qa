# Denial-case set

30 synthetic coverage denial letters with known intended verdicts. The set has three jobs:

1. **Demo cases.** Clean letters whose verdict the policy documents settle, for the live demo and the video.
2. **Letter gallery.** The 10 rows marked `demo=yes` are the letters offered on screen as samples.
3. **Denial-case evaluation set.** The agent's verdict on each letter is compared with `intended_outcome`. No row is used for a score until a human has verified it (see "Review protocol").

Status: agent-drafted on Oct 26, 2026. **Not yet human-verified.** Every row is a draft until Alvaro keeps or edits it.

## Every letter is synthetic

No letter describes a real member, provider, claim, or payer action. Member names are "A. Sample" style, IDs are `00000000-SAMPLE`, and providers are "Sample ..." businesses. Each letter starts with `SAMPLE LETTER FOR DEMONSTRATION. NOT A REAL NOTICE.` and ends with a line saying it is synthetic.

Payer names are real only where a corpus document is that payer's own public policy. "Medicare" appears on the Original Medicare samples (Part A and Part B), because the CMS manuals and booklets in the corpus are Medicare's policy. Every managed care plan, dental plan, drug plan, KidCare plan, provider, and employer is a generic "Sample ..." name. The corpus contains no plan-specific policy for any real Florida Medicaid, KidCare, Medicare Advantage, or Part D plan, so no real plan name is used.

## Files

| File | What it is |
|---|---|
| `cases.csv` | One row per case. Columns below. |
| `letters/<id>.txt` | The full letter text, 600 to 1,500 characters. |
| `verify.py` | Stdlib-only checker. `python cases/verify.py` from the repo root. Exit 0 means every row passed. |

## How a case is built

1. Pick a rule in the corpus that decides a service: a coverage statement, a limit, a condition, or an exclusion.
2. Open the page text at `data/text/<doc_id>/pNNN.txt` and copy the exact sentence. That sentence is the `hinge_quote`; its document and page are `hinge_doc_id` and `hinge_page`.
3. Write the payer's stated reason so that it either matches the rule (consistent), is contradicted by the rule on its face (inconsistent), or depends on a fact the documents do not state (not_settled).
4. Write the letter in the register of the program's real notice: a Notice of Adverse Benefit Determination for Florida Medicaid and KidCare plans, a Medicare Summary Notice for Part A and Part B, a denial notice for Medicare Advantage and Part D, an EOB for the commercial plan. The letter states every case card field in plain words: payer, program, member age, service and code, dates of service, amount, the reason, the letter date, and the appeal deadline when the row has one.
5. Run `verify.py`.

Page numbers are the page-file index (`p005.txt` is page 5), the same convention as `golden/golden.csv`. They are not the page numbers printed in the PDF footer.

## Verdict rule

The three verdicts are the product's fixed phrasings:

| `intended_outcome` | Verdict on screen | When |
|---|---|---|
| `consistent` | the denial matches the policy | The hinge quote states the exclusion, limit, or requirement the letter cites, and the letter's facts meet it. |
| `inconsistent` | the denial appears inconsistent with the policy | The hinge quote contradicts the stated reason on its face: a limit lower than the policy's, an age rule the policy does not have, a prior authorization the policy does not require, or an exclusion that the policy's own exception covers. |
| `not_settled` | the documents do not settle it | The decision turns on a fact the documents do not state (authorized hours, a plan of care, a member's condition, a product list incorporated by reference) or a rule outside the corpus. The hinge quote is the closest relevant sentence, and `notes` says why it is not enough. |

The verdict is about the stated reason against the written rule. It is never a judgment about whether the care was needed. Letters state what was denied and why in coverage terms only.

## Mix

| | Count |
|---|---|
| Rows | 30 |
| Inconsistent | 14 |
| Consistent | 10 |
| Not settled | 6 |
| Traps | 4 |
| Demo letters | 10 (5 inconsistent, 3 consistent, 2 not settled, 1 trap) |

| Program (`program`) | Rows |
|---|---|
| Florida Medicaid MMA (`florida_medicaid_mma`) | 11 |
| Florida Medicaid LTC (`florida_medicaid_ltc`) | 3 |
| Florida KidCare (`florida_kidcare`) | 3 |
| Medicare Part B (`medicare_b`) | 4 |
| Medicare Advantage (`medicare_advantage`) | 3 |
| Medicare Part D (`medicare_part_d`) | 3 |
| Medicare Part A (`medicare_a`) | 2 |
| Outside the corpus, commercial employer plan (`unknown`) | 1 |

There are two dual-eligible rows: dc-012 (LTC member, age 74, with Medicare on file) and dc-021 (a Part B visit for a QMB enrollee, Florida Medicaid secondary). Both have `jurisdiction=both`.

Services covered: private duty nursing, home health visits, personal care, dental, respiratory DME, non-emergency transportation, inpatient and emergency hospital care, diabetic supplies, behavior analysis, prescription drugs, LTC home and community-based services (meals, home adaptation, adult day care), chiropractic, physical therapy, eyeglasses, hearing aids, ambulance, QMB cost-sharing, hospice, and skilled nursing facility care.

Six letters have no appeal deadline on purpose (dc-008, dc-009, dc-011, dc-021, dc-025, dc-030), so the intake must leave that field empty. dc-015 claims a 30-day appeal window where the KidCare guide gives 60 days, so the deadline step has one wrong deadline to catch.

### Traps

| Id | Trap | Expected |
|---|---|---|
| dc-002 | Reads like age discrimination; PDN really is limited to recipients under 21. | consistent |
| dc-011 | A treatment question disguised as a pharmacy notice ("Should I take half of my insulin dose..."). | Scope refusal (`out_of_scope`); no verdict, no dosing content. Recorded as `not_settled`. `scope_check` in `policyqa/intake.py` flags this letter and no other. |
| dc-024 | Looks like it breaks the emergency protections; the manual's own example excludes an unrelated biopsy during fracture care. | consistent |
| dc-030 | A commercial employer plan, a program not in the corpus. | not_settled; routing should say no document governs it. |

## Columns

`id`, `program`, `member_age_group`, `jurisdiction` (Florida, Federal, or both), `service`, `service_code` (HCPCS, CPT, or CDT when known, else blank), `denial_reason` (the letter's reason, verbatim), `intended_outcome`, `hinge_doc_id`, `hinge_page`, `hinge_quote`, `amount_billed` (blank for requests not yet billed), `dates_of_service` (YYYY-MM-DD or START/END), `letter_date`, `appeal_deadline_claimed` (blank when the letter states none), `difficulty`, `trap`, `demo`, `notes` (what the case tests and what to check first), `payer_name` (the issuer named in the letter; added after `notes` so the specified column order stays intact).

`program` and `member_age_group` use the case card enums in `policyqa/intake.py`.

## What verify.py checks

- Enums, ISO dates, date ranges, and amounts are valid.
- The hinge quote appears in `data/text/<hinge_doc_id>/p<NNN>.txt` after whitespace is normalized. If the document's text folder is missing on the machine (fl-24 and hipaa-01 to 04 today), the row is reported as "unverifiable here", not as a failure. No row cites those documents now.
- Each letter exists, is 600 to 1,500 characters, starts with the sample line, and ends with the synthetic line.
- Each letter contains its amount (as `$1,234.00`), its dates of service and letter date (as `September 1, 2026`), its denial reason verbatim, its service code when set, and its deadline when set.
- The set has 30 unique ids, the 14 / 10 / 6 outcome mix, 4 traps, and 10 demo rows with the demo minimums.

## Review protocol

Alvaro verifies every row before the set is used for a score or shown in the demo. He uses a review page, not the CSV: one case at a time, the letter in large text beside the hinge quote with its document and page, the intended verdict, and the notes. There are three buttons:

- **Keep**: the letter is realistic, the quote is on the page, and the intended verdict follows from the quote.
- **Edit**: the verdict, the quote, or a letter field needs a change. He types the change and it is applied to the row.
- **Reject**: the case is dropped from the set (for example a rule he reads differently, or a letter that is not realistic).

Verdicts are saved server-side, in the same way as the Golden Set Review. The review page is not built yet. Until it exists, every row is an agent draft. After review, `verify.py` must pass again and the outcome mix may change; the mix rules in `verify.py` should then be updated to the verified counts.

What a verifier should look at first is in each row's `notes`. The rows most open to a different reading are dc-008 (whether days 46 to 51 were emergency services), dc-013 (LTC home adaptation against the MMA DME ramp exclusion), dc-017 (a plain-language guide sentence against a plan's drug list), and dc-021 (a provider statement, not a payer notice).
