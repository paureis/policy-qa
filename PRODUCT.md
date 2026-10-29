# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two primary audiences, designed for together (confirmed by Alvaro, Oct 26, 2026):

- **Patients and caregivers** on Florida Medicaid or Medicare, holding a coverage denial letter or an explanation of benefits (EOB). Stressed, not technical, often on a phone with a photo of the letter.
- **Billing staff** at clinics and health plans who handle denials as part of their job.

Shared situation: a denial in hand, a deadline they may not know, and no idea which rule governs the service. Their job: find out whether the denial holds against the written policy and, if it does not, get the appeal letter, the evidence list, the deadline, and where to file. Most people in this situation never appeal (KFF 2025: denials are rarely appealed, yet 43 to 67 percent of appeals succeed).

**Device: phone first** (confirmed). The primary path is photographing the letter with the phone camera in the browser. Uploading a PDF or pasting text from a desktop is supported but second.

Secondary audience: the Meta Global AI Developer Hackathon judges (indie track, Oct 26 to Nov 4, 2026), who evaluate the live demo, a three-minute video, and the public repository against a rubric of Impact 30%, Use of Meta AI tooling 25%, Technical depth 20%, Demo 25%.

## Product Purpose

Recourse turns a coverage denial into a case, and the case works itself. The user drops in a denial letter or EOB as a photo, PDF, or text. Recourse reads it into a case card, works out which program and policy govern the service, investigates the written rules, argues the payer's side first, and returns one of three verdicts with the rule quoted and cited to the page: the denial matches the policy, the denial appears inconsistent with the policy, or the documents do not settle it. For an inconsistent denial it drafts the appeal letter, every sentence carrying a verified citation, plus the evidence checklist the policy implies, the filing deadline with a day count, and where to file. For a consistent denial it gives a plain explanation and what would have made the service covered.

Success: a photo of a letter becomes a cited verdict and a filing-ready letter in under a minute, with every claim verifiable against a public document, and with measured accuracy (golden set, denial-case set, judge validated against human verdicts) before any number is shown.

## Positioning

A coverage-denial appeal agent, not a policy question-and-answer assistant and not a basic retrieval demo. The mechanism a neighbor could not truthfully copy:

- Citations are checked, not trusted. A quote must exist verbatim in the cited passage (document, page) or the finding is struck out on screen; an answer left with no valid citation becomes an abstention.
- The agent argues the payer's side (steelman) before deciding, and says "not settled" when the documents do not settle it.
- Every step is measured against a human-verified golden set, and the judge that grades answers is itself validated against human verdicts before an accuracy number is quoted.
- Scope is coverage and billing rules only. It never gives medical advice; treatment or diagnosis questions are refused with an explanation of what the product does instead.

## Operating Context

- **Case flow** (fixed vocabulary): Intake, Routing, Investigation, Steelman, Verdict, Action, Trust.
- **Programs covered:** Florida Medicaid MMA, LTC, KidCare; Medicare Part A, Part B, Medicare Advantage, Part D. Dual-eligible or ambiguous cases are investigated under Florida Medicaid and Medicare side by side, with the difference stated.
- **Corpus:** 64 public PDFs, 2,589 pages (30 Florida Medicaid, 30 federal Medicare and Medicaid, 4 HIPAA), jurisdictions `Florida` and `Federal`, listed in `corpus/manifest.csv`. Documents are never redistributed in the repo; they are fetched from their public source URLs.
- **Models:** generation and vision on Muse Spark 1.3 (`muse-spark-1.3`) through the Meta Model API (mandatory for the hackathon); Muse Spark Open on Baseten for the open-weights comparison; Claude as the answer judge, validated against human verdicts. Retrieval runs local open models on CPU (bge-small-en-v1.5 embeddings, hybrid BM25 plus dense with reciprocal rank fusion, MiniLM-L-6 reranker over 20 candidates on the answering path).
- **Stack:** `web/` is Next.js 16 (App Router, React 19, TypeScript, Tailwind 4), deployed to Vercel at https://recourse-murex.vercel.app. `api/` is FastAPI over the `policyqa` package, deployed to Modal at https://alpau-reis--recourse-api.us-east.modal.run (one warm container; `deploy/README.md`). Since Oct 28 the whole chain is deployed: intake, investigate, verdict, letter, critic, second opinion, page images and highlights.
- **Division of labor:** Alvaro owns the front end, local runs, labeling, deploys, and the video. Claude owns the agent, the API, the evals, and the documents.
- **Hackathon constraints:** new work only; the demo may show only what was built during the event (Oct 27 to Nov 4). Pre-event dataset and retrieval groundwork are disclosed in the README timeline and stay out of the demo. Public repository, three-minute demo video, submission by Nov 4, 9:00 PM ET.
- **Demo material:** synthetic sample denial letters (30, with reviewed verdicts) for the denial-case eval set and the live demo. No real letters. The public sample case on the landing is a recorded run of dc-001 through the API (Oct 28, 2026): real policy pages, quotes, vision checks, costs and second opinion; only the letter is synthetic, and the page says so once.

## Capabilities and Constraints

Planned product capabilities, built from Oct 27 (dates in README):

- Intake from photo, PDF, or text into an editable case card: program, member age group, service and code, dates, amount, the payer's stated reason, letter date, claimed deadline. The user corrects anything wrong.
- Program routing, including dual-eligible side by side.
- Investigation agent: targeted questions against the corpus (covered, limits, conditions and prior authorization, exclusions, appeal rights and deadlines), each finding a verbatim quote with document and page, checked by a verifier. Unsupported findings are struck out on screen, not hidden.
- Steelman pass, then one of three verdicts naming the rule and the gap between the letter's reason and that rule.
- Action: draft appeal letter with a citation on every sentence; evidence checklist derived from the policy's conditions; deadline with a day count and the filing path, cited from the appeals documents; for a consistent denial, a plain explanation and what would have made the service covered.
- Trust panel: verification coverage (claims supported over claims made), cost of the case, time taken, and the full trace.
- Scope guardrail: treatment and diagnosis questions are refused with an explanation.

Hard constraints future work must preserve:

- Never medical advice. No treatment or diagnosis content, ever.
- No claim without a verified (document, page) citation. Chunks never cross a page, because a citation that spans pages cannot be honest.
- Only three verdicts: consistent with the policy, inconsistent with the policy, not settled by the documents. Abstention is a correct outcome, not an error state.
- Accuracy, coverage, and latency numbers shown anywhere come from a recorded run in `results/`, never typed in.
- The case card is user-correctable before anything downstream runs.

Terminology (use exactly): case, case card, program, finding, verifier, verified citation, steelman, verdict, appeal letter, evidence checklist, deadline with day count, filing path, trace, verification coverage, abstention. Golden-set question types: fact, num, proc, multi, adv, none.

Language (confirmed): English UI in plain language for a reader with no insurance background. **Spanish is a stretch feature**, not a commitment of this build. Appeal letters to the payer are in English.

Explicitly undecided or stretch: Spanish UI; voice intake with Muse Voice Transcribe; saving the letter as a file; dual-eligible side by side if the core slips. Accessibility conformance level is not yet decided (see below).

## Brand Commitments

- **Name:** Recourse. **One-line description:** "A coverage denial becomes a case, and the case works itself."
- **Voice as observed in the README and DECISIONS.md** (not yet confirmed as binding; treat as the house default until Alvaro says otherwise): plain declarative sentences, numbers always with their source, no superlatives or exclamation, candid about limits and about what was not built. The product says "the documents do not settle it" rather than guessing.
- Binding product vocabulary: the three verdict phrasings and the seven case-flow step names above.
- No logo, wordmark, color, or other visual identity exists yet. Nothing visual is committed.
- Meta tooling must be visibly credited in the demo (Muse Spark for vision and generation, Muse Spark Open on Baseten, Muse Code during the build); this is a hackathon requirement, not a styling instruction.

## Evidence on Hand

- Problem evidence: KFF 2025 prior-authorization analysis as quoted in `README.md` (denial rates about 12% Medicare Advantage, 14% Medicaid managed care, 18% ACA marketplace; overturn rates on appeal 67%, 47%, 43%; most denials never appealed).
- Dataset: `corpus/manifest.csv` (64 documents with source URLs) and `golden/golden.csv` (160 questions, six types, LLM-drafted and human-verified row by row).
- Retrieval results with full configs: `results/*.json`; reasoning and tables in `DECISIONS.md` (hybrid plus MiniLM-20 reranker: all@10 0.712 on 139 rows, p50 415 ms on Alvaro's CPU).
- Internal tooling: `review/judge-review.html`, a one-answer-at-a-time grading page for judge validation.
- Absences future work must not fabricate: no real users, testimonials, customers, partners, or press; no real denial letters (samples are synthetic); no generation accuracy numbers yet (pending the Muse Spark runs and judge validation); no pricing, licensing, or compliance claims (HIPAA documents are in the corpus as subject matter, not as a compliance certification); the full 64-document retrieval run is pending (59 reachable so far).

## Product Principles

1. **The quoted rule is the product.** Nothing is asserted without its document and page, and the user can always reach the quote.
2. **Honest about uncertainty.** Three verdicts, abstention counts as success, struck-out findings stay visible, and the trust panel shows coverage and cost.
3. **The stressed person on a phone comes first.** One photo to a cited verdict with the fewest steps; the deadline and where to file are never buried.
4. **Coverage, never care.** Treatment and diagnosis questions are refused with a reason and a pointer to what the product does.
5. **Measured before shown.** Every number in the product or the pitch traces to a recorded run, and the judge is validated against people first.

## Accessibility & Inclusion

- Primary users are stressed and not technical, often on a phone: plain-language copy at a reading level that assumes no insurance background; the verdict and the deadline must be understood without reading the citations.
- The programs served are by definition populations that skew older or disabled (Medicare; Florida Medicaid LTC) or are caregivers acting for children (KidCare). Expect low vision, large system text, and one-handed phone use.
- English only for this build; Spanish is a recorded stretch. Florida publishes Medicaid materials in English, Spanish, and Haitian Creole, so other languages remain an open item.
- No conformance standard (for example a WCAG level) has been set; undecided.
