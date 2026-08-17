# Bassetti CV Parser POC

> Bassetti interview POC / unofficial demo. A local, human-in-the-loop CV transcription workbench — not an official Bassetti product or template.

This repository is a runnable interview demonstration. It extracts **only information explicitly present** in a CV into a fixed schema, displays source evidence and uncertainty, records recruiter corrections, and unlocks JSON/DOCX export only after every required field has been confirmed.

It does **not** score, rank, match, recommend, reject, or otherwise make employment decisions.

## Quick start

Tested with Python 3.12 on macOS. No Node build, database, account, paid API, or network connection is required.

```bash
git clone https://github.com/wangkeyu-u/bassetti-cv-parser-poc.git
cd bassetti-cv-parser-poc

# Use an isolated environment for a normal machine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Generate/re-generate the fictional PDFs and gold fixtures
PYTHONPATH=. python scripts/generate_samples.py

# Start the app
PYTHONPATH=. python run.py
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). If that port is occupied:

```bash
PYTHONPATH=. python run.py --port 8877
```

The application uses Python's standard-library HTTP server; `pdfplumber`, `python-docx`, and `reportlab` cover document processing and fixtures.

## Test and validation

```bash
# Unit + full HTTP workflow tests
PYTHONPATH=. python -m unittest discover -s tests -v

# Compare every bundled sample against its human-authored gold fixture
PYTHONPATH=. python scripts/validate_fixtures.py
```

Latest verified result:

- 7/7 automated tests passing.
- 24/24 schema groups correct on three bundled fictional fixtures (100%).
- This is explicitly a **demo measurement** on a tiny controlled set, not Bassetti internal data and not a production-quality or 95% claim.
- DOCX export rendered to PNG through LibreOffice and visually checked with no clipping or overlap.

The validation report is saved at [`fixtures/validation_summary.json`](fixtures/validation_summary.json). Gold fixtures are under [`fixtures/gold/`](fixtures/gold/).

## 3–5 minute interview demo

1. **Set the boundary (20 seconds).** On the opening screen, point out “Evidence first. Judgment stays human” and the explicit no-scoring/no-ranking statement.
2. **Happy path (45 seconds).** Choose `normal_single_column`. Extract it. Show structured values, PDF page evidence, confidence, and the fact that `English: Fluent` remains `Fluent` while CEFR is `Not specified`.
3. **Human control (60 seconds).** Edit one field, click **Save edit**, then **Confirm**. Flag another for follow-up. Open **Audit record** to show timestamp, field, old/new value, status, and action.
4. **Exceptions (45 seconds).** Start again with `mixed_fr_en_ambiguous`. Show phone as **Not found**, the day/month ambiguity, overlapping dates, the sensitive-information warning, mixed French/English values, and no inferred CEFR.
5. **Approval gate and export (45 seconds).** Confirm all eight schema groups (confirming “Not found” is an explicit human assertion). Export JSON and DOCX. Open the DOCX to show the standardized, unofficial company profile.
6. **Safe fallback + measurement (30 seconds).** Click **Return to review** to lock exports again without deleting values/audit history. Show the **demo measurement** area and its tiny-dataset disclaimer.

## Supported workflow

- Input: PDF and DOCX up to 10 MB.
- Text PDFs: text extraction with page-number evidence.
- DOCX: paragraphs and tables; evidence has no page number because DOCX pagination is renderer-dependent.
- Fixed groups: name, email, phone, location, education, work experience, skills, and languages.
- Per field: editable structured value, evidence quote, page when available, high/medium/low confidence, explicit `Not found`, ambiguity note, and review status.
- Actions: save edit, confirm, flag follow-up, return to review, and start again.
- Export: reviewed JSON plus a readable unofficial DOCX candidate profile.
- Audit: local JSON session record with UTC time, field, old/new values, old/new status, and action. Writes use a temporary file + atomic replace; changes are not silently overwritten.

Grouped values (`education`, `work_experience`, `skills`, `languages`) are intentionally shown as JSON arrays in the POC editor. This keeps every schema field transparent and makes live demos of structural corrections possible without a heavier form framework.

## Architecture

```text
PDF / DOCX
    │ input validation (extension, signature, size, readable text)
    ▼
local text reader ──► conservative deterministic parser
                          │
                          ▼
                 fixed schema + evidence + ambiguity
                          │
                          ▼
               browser-based recruiter review
                 │ edits / confirms / follow-up
                 ▼
         atomic local JSON session + audit trail
                          │ all 8 groups confirmed
                          ▼
                    JSON + DOCX export
```

Key modules:

- [`bassetti_poc/extractor.py`](bassetti_poc/extractor.py) — input validation, PDF/DOCX reading, conservative parsing, evidence, sensitive-data warnings.
- [`bassetti_poc/schema.py`](bassetti_poc/schema.py) — fixed schema and export mapping.
- [`bassetti_poc/storage.py`](bassetti_poc/storage.py) — atomic local session/audit store.
- [`bassetti_poc/exporter.py`](bassetti_poc/exporter.py) — approval gate and JSON/DOCX renderers.
- [`bassetti_poc/app.py`](bassetti_poc/app.py) — local HTTP routes, errors, security headers, uploads, review actions, and downloads.
- [`static/`](static/) — accessible, dependency-free review interface.

The UI uses a restrained French industrial/editorial direction: warm white, charcoal/deep brown, Bassetti orange `#EC6408`, strict rules and grids, limited status colors, and no “AI tech” ornament. The DOCX uses a `standard_business_brief`-derived numeric style system with an explicit compact candidate-profile override (Letter, 0.7/0.78-inch margins, Aptos 10.5 pt, fixed two-column contact grid, restrained orange/charcoal palette).

## Fictional demo data and failure coverage

All sample names, employers, schools, emails, phone numbers, and identifiers are invented. `.example.test` addresses cannot be real mail destinations.

| Fixture | Purpose |
|---|---|
| `normal_single_column.pdf` | Normal single column, complete core data, `English: Fluent` without CEFR |
| `complex_two_column.pdf` | Two-column/table layout with interleaved PDF reading order and wrapped skills |
| `mixed_fr_en_ambiguous.pdf` | French/English mix, missing phone/icon scenario, incomplete language levels, ambiguous date, overlap, synthetic sensitive-ID warning |

Automated exception coverage includes unreadable/blank PDF, invalid type/signature, double-column interleaving, mixed language, numeric date ambiguity, date overlap, language without CEFR, missing field, icon-without-readable-text behavior, sensitive-information detection, approval-gate failure, audit preservation, and safe reset.

## Privacy and security boundary

- The default path is deterministic and offline; there is no LLM or external API integration and therefore no API key.
- Bind defaults to `127.0.0.1`, not the LAN. Do not change `--host` to a public interface for real CVs without authentication, TLS, access control, and a retention policy.
- Uploads are processed in memory. The original CV is not retained. Extracted session/audit JSON is stored in `data/sessions/` and is gitignored.
- The UI is protected with CSP, clickjacking, MIME-sniffing, referrer, and no-store headers.
- Potential sensitive terms are warned about and excluded from the fixed output schema. This is a narrow warning mechanism, not a complete DLP solution.
- There is no authentication because this is a single-user localhost POC. Treat generated exports and local session files as personal data if used beyond the fictional fixtures.
- To erase local POC records, stop the server and delete the individual JSON files under `data/sessions/`; keep only `.gitkeep`. This is deliberately a manual, explicit operation.

## Known limitations

- Scanned/image-only PDFs are rejected with a clear OCR-not-enabled message. Production should add a locally hosted OCR stage plus image-quality confidence and page-region evidence.
- Deterministic rules work for the three controlled fixtures, not arbitrary global CV formats. Complex tables, headers, and reading order can still split text.
- Phone/location/date recognition is conservative; ambiguity is preferred over guessing.
- It does not normalize degree taxonomies, infer seniority, translate content, map languages to CEFR, or resolve overlapping jobs.
- DOCX evidence cannot reliably cite a page number until rendered.
- Sessions are files, so this is single-node only; there is no concurrency ownership, login, encryption-at-rest, retention job, or central audit service.
- The standard-library HTTP server is suitable for a local demonstration, not production deployment.

## Suggested production integrations

1. Replace the file store with encrypted, access-controlled storage and append-only enterprise audit events; add SSO/RBAC, retention/deletion policies, malware scanning, and observability with PII-safe logs.
2. Add OCR/layout understanding with page bounding boxes and side-by-side PDF evidence highlighting.
3. Introduce a versioned schema and adapter for the authorized company DOCX template/ATS, retaining a recruiter approval checkpoint.
4. Build a representative, consented, de-identified multilingual evaluation set; report precision/recall and missing/ambiguous rates by field and layout rather than one headline number.
5. If an optional LLM is later added, require explicit environment-variable activation, an approved endpoint/data-processing agreement, prompt-injection defenses, structured-output validation, and this deterministic local fallback. Never let it score/rank/reject candidates.

## Repository hygiene

No real candidate data, secrets, API keys, or official Bassetti assets are included. Runtime sessions, uploaded files, temporary renders, and exports are gitignored. The generated `output/demo_candidate_profile.docx` is a fictional QA artifact and can be regenerated from the code.
