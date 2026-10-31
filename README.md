# Northline RCA

Root-cause analysis workspace for an API manufacturing site. A quality investigator drops a deviation report, a shift note, or an email. A LangGraph workflow reads it, fills the RCA record, and drafts a 5 Whys chain, a 6M fishbone, cause hypotheses, evidence gaps, and CAPA proposals. The investigator reviews every field. Nothing the model proposes is an established root cause until a qualified person confirms it against evidence.

This repository is a private take-home. Do not publish the source, the sample documents, screenshots, or a demo recording to GitHub or any public host.

## What you can do with it

1. Attach a PDF or `.eml`, or paste text, and run **Analyse source**.
2. Watch the assistant move through the graph. Newly filled fields are highlighted and badged **AI extracted** or **AI suggested**.
3. Review the record. Accept extracted facts, edit them, confirm a cause only when it has an evidence note, and mark gaps resolved.
4. Ask the assistant to change the draft: “add a why about the alarm”, “set the batch to ATV-CA-26-0142”, “suggest another preventive CAPA”, “redraft the fishbone”.
5. Sign the QA review. Approval requires a reviewer name and an explicit acknowledgement that AI suggestions were reviewed.
6. Save. Reopen the investigation from the library. The history drawer shows what changed between saves.

## Samples

| File | Incident |
| --- | --- |
| `samples/DEV-2026-1184_atorvastatin_impurity.pdf` | Atorvastatin calcium batch ATV-CA-26-0142. RS-3 0.18% (limit 0.15%) and assay 98.2% (limit 98.5–101.5%) after the crystallizer jacket left 8°C and sat at 17°C for 46 minutes. Valve V-17 hunting, a suppressed cooling-water alarm, a short seed charge, and a manual HPLC integration. |
| `samples/shift_note_metformin_lod.txt` | Informal note from drying supervisor A. Iyer. Metformin hydrochloride MFH-26-2033 left tray dryer TD-12 at 0.42% LOD (limit 0.30%). No deviation number yet. |
| `samples/email_omeprazole_near_miss.eml` | Production email. Methanol drum MD-4418 was staged for omeprazole intermediate OMP-INT-26-077. Caught before the charge. Barcode override with a blank reason. |

The assistant panel loads these three directly. The PDF is already built. To regenerate it: `backend/.venv/bin/python samples/generate_deviation_pdf.py`.

## Architecture

```text
browser (React + Redux Toolkit, Vite)
    |  /api  proxied to the API
FastAPI
    |-- ingest: PDF (pypdf), .eml (stdlib email), or pasted text
    |-- analyze graph (LangGraph + Groq via langchain-groq)
    |-- chat graph (plan edits, optional redraft, then apply in Python)
    |-- investigations: SQLAlchemy JSON document + list columns + audit rows
PostgreSQL
```

The browser keeps the RCA document in Redux. The form and the assistant read the same slice, so a chat edit and a keystroke are the same kind of update. The document stored in Postgres is that same JSON. A few columns (deviation number, title, product, batch, severity, status) exist only so the library can list records without opening every document.

AI output is stored with flags, not just text:

- Scalar fields (`batch_lot`, `description`, …) have `origin` (`empty` | `ai` | `user`) and `confirmed`.
- Causes have `ai_suggested`, `evidence`, `grounded`, `evidence_supported`, `confirmed`, and `confirmed_by`.
- `grounded` is not the model’s opinion. After each analysis, chat edit, and save, Python checks the evidence note against the uploaded source (`app/services/grounding.py`). A number in the note that never appears in the source forces the cause down to an unconfirmed, low-confidence hypothesis.
- A person may still confirm a cause whose evidence was not in the file (an interview, a historian printout). The badge then reads **Confirmed**, and **Not in source** stays visible. The QA acknowledgement is what makes that a human decision.
- Chat is not allowed to set status to `approved`. Approval is a named sign-off in the review section, checked again on the server.

### Analyse graph

```mermaid
flowchart TD
  A[prepare_source] --> B[extract_fields]
  B --> C{Product, batch, title, or description found?}
  C -->|no, and this was the first pass| B
  C -->|yes, or the retry is spent| D[investigate]
  D --> E[identify_causes]
  E --> F[evidence_gaps]
  F --> G[recommend_capa]
  G --> H[assemble]
```

`prepare_source` and `assemble` are Python. The five steps between them each make one structured Groq call (`with_structured_output`). If that call fails schema validation, `complete_structured` retries up to three times and switches method (`function_calling`, then `json_schema`, then `json_mode`). The graph itself retries extraction once when the first pass comes back empty, so a blank extraction is visible as “retried” on the assistant stepper.

`assemble` builds the record the form already understands, stamps new text as AI-suggested, runs the grounding check, and adds gaps for missing deviation number, batch, product, or times. It does not invent those identifiers.

### Chat graph

```mermaid
flowchart TD
  P[plan_edit] --> Q{Redraft a whole section?}
  Q -->|yes| R[regenerate]
  R --> S[apply_edits]
  Q -->|no| S
```

`plan_edit` returns a short reply plus a list of operations (`set`, `append_why`, `add_fishbone`, `add_root_cause`, `add_factor`, `add_gap`, `add_capa`, `add_team`, `remove`, `confirm`, `update_item`, `regenerate`). `apply_edits` is plain Python. Unknown paths are rejected. Confirming a cause, why, or fishbone item with an empty evidence note is rejected, and the reply says so. `regenerate` re-enters the same node functions used by the analysis graph (`whys`, `fishbone`, `causes`, `gaps`, or `capa`) and replaces that section with a new AI draft.

## Project layout

```text
backend/app/main.py                 FastAPI app, CORS, error handler
backend/app/schemas.py              RCA document stored in Postgres and edited in the browser
backend/app/ai_schemas.py           Pydantic models the LLM is allowed to return
backend/app/services/text_extract.py
backend/app/services/llm.py         structured Groq calls and retries
backend/app/services/graph/analyze.py
backend/app/services/graph/chat.py
backend/app/services/graph/prompts.py
backend/app/services/graph/runners.py
backend/app/services/assemble.py
backend/app/services/operations.py  allow-listed chat edits
backend/app/services/grounding.py
backend/app/services/repository.py  save, reload, approval rule, audit
frontend/src/store/                 investigation, assistant, and library slices
frontend/src/workflows.ts           analyse and chat, then dispatch into Redux
frontend/src/components/            split layout: record | assistant
samples/                            three demo incidents
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Database, model name, whether `GROQ_API_KEY` is set |
| POST | `/api/ingest` | Multipart `file` and/or form field `text` |
| POST | `/api/ai/analyze` | Run the graph, return the record as JSON |
| POST | `/api/ai/analyze/stream` | Same graph as server-sent events (`phase`, then `result`) |
| POST | `/api/ai/chat` | `{ message, history, record }` → updated record |
| GET, POST | `/api/investigations` | List, create |
| GET, PUT, DELETE | `/api/investigations/{id}` | Open, save, delete |
| GET | `/api/investigations/{id}/audit` | Save history |
| GET | `/api/samples` and `/api/samples/{filename}` | Demo inputs |

Interactive docs: `http://127.0.0.1:8077/docs`.

Approval returns 422 unless `approval.reviewer_name` is set and `approval.acknowledged_ai_review` is true. A confirmed cause or factor with a blank evidence note is also rejected.

## Run it locally

You need Python 3.12+, Node 20+, and Docker (or an existing Postgres). The UI is `http://127.0.0.1:41731`. The API is `http://127.0.0.1:8077`. The Vite dev server proxies `/api`, so the browser talks to one origin.

### 1. Postgres

From the repository root:

```bash
docker compose up -d
```

`docker-compose.yml` maps host port **54329** to Postgres 5432, user `rca`, password `rca`, database `rca`. Wait until `docker compose ps` shows the database as healthy.

### 2. Environment

```bash
cp .env.example .env
```

Set `GROQ_API_KEY` in `.env`. Leave `GROQ_MODEL` as `llama-3.3-70b-versatile` unless Groq has retired that id; if a call fails with a model error, set `GROQ_MODEL` to another current Groq model (the brief also names `gemma2-9b-it`) and restart the API. Do not commit `.env`.

| Variable | Purpose |
| --- | --- |
| `GROQ_API_KEY` | Required for analyse and chat. The rest of the app runs without it. |
| `GROQ_MODEL` | Default `llama-3.3-70b-versatile`. |
| `DATABASE_URL` | Default `postgresql+psycopg://rca:rca@localhost:54329/rca`. |
| `CORS_ORIGINS` | Defaults include `http://127.0.0.1:41731`. |

### 3. API

macOS / Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload - -host 127.0.0.1 --port 8077
```

Windows (PowerShell):

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8077
```

Tables are created on startup (`create_all`). That is deliberate for this take-home; there is no Alembic migration chain.

### 4. UI

```bash
cd frontend
npm install
npm run dev
```

Open [http://127.0.0.1:41731](http://127.0.0.1:41731).

### Checks

```bash
cd backend && .venv/bin/python -m pytest && .venv/bin/ruff check app tests
cd frontend && npm run lint && npm run build
```

Backend tests use SQLite and a scripted model. One test uses Postgres at `postgresql+psycopg://rca:rca@127.0.0.1:5432/rca_test` when that database exists, and skips otherwise. The dev database from Docker is on port 54329 and is not required for the unit tests.

## Demo recording (about 5–8 minutes)

Record the browser, not the terminal. Have the API running with a real `GROQ_API_KEY` before you start. Use the atorvastatin PDF first; it has the most to investigate.

1. **Empty workspace (about 30 seconds).** Show the split layout. Say that the form is not filled by hand: the assistant on the right is the way in. Point at the banner if you want to show that a missing key is visible, then dismiss that case and use a configured key.
2. **PDF in, record out (about 2 minutes).** Click the Deviation PDF sample, then **Analyse source**. Leave the stepper visible. When the form fills, scroll the highlighted fields: deviation number DEV-2026-1184, batch ATV-CA-26-0142, the two OOS results, quarantine. Accept the identification section.
3. **Investigation (about 2 minutes).** Show the 5 Whys and the fishbone. Open a root cause. Point at **AI suggested**, **In source** or **Not in source**, and the disabled confirm button when evidence is empty. Confirm one cause that cites the temperature excursion or V-17. Leave another unconfirmed and say that saving will not promote it.
4. **Gaps and CAPA (about 1 minute).** Show a gap (alarm audit trail, missing balance printout, or reinjection) and one corrective plus one preventive action. Accept one proposal.
5. **Chat edit (about 1 minute).** Ask for one change, for example “add a why about the suppressed differential-pressure alarm” or “set the batch disposition to Quarantine”. Show the form update and the reply. If you ask to confirm a cause with no evidence, the reply should refuse.
6. **Sign and save (about 1 minute).** Enter a reviewer name, tick the acknowledgement, **Approve and sign**, then **Save**. Open **Library**, reopen the record, and open **History** so the create (and a second save, if you edit the batch and save again) is visible.
7. **Second input, shorter (if you have time).** Paste the metformin shift note or load the email. Point out that the note has no deviation number, so a gap is raised instead of a fabricated one, and that the email is a near miss with no product charged.

If a model call fails or the stepper shows “retried”, say what that is: schema validation failed and the node ran again. Do not treat a hypothesis as the site’s conclusion.

## Code walkthrough (about 5–10 minutes)

A reasonable order if someone is watching the files:

1. **`frontend/src/components/Workspace.tsx` and `AssistantPanel.tsx`.** Split layout. Analyse calls `workflows.ts`, which ingests, then consumes the server-sent events and dispatches into the investigation slice and the assistant slice.
2. **`frontend/src/store/investigationSlice.ts`.** One document. Badges, highlights, confirm, and the rule that approval is not a casual status change.
3. **`backend/app/routers/ingest.py` and `services/text_extract.py`.** PDF, email, pasted text. Scanned PDFs and Outlook `.msg` fail with a clear error.
4. **`backend/app/services/graph/analyze.py`.** The nodes and the one conditional retry. `runners.py` is the actual model call; the graph is the order.
5. **`backend/app/services/llm.py` and `ai_schemas.py`.** Structured output, retries, no API key in the error text.
6. **`prompts.py`, `assemble.py`, `grounding.py`.** What the model is forbidden to invent, and the check that runs afterwards.
7. **`graph/chat.py` and `operations.py`.** The model proposes operations. Python applies them and can refuse.
8. **`repository.py` and `models.py`.** JSON document, list columns, audit diff, the approval rule enforced again on save.

The tests in `backend/tests` mirror that story: grounding rejects a number that is not in the source, the graph retries a blank extraction, chat sets a batch without marking it as an AI guess, and save/reload keeps `ai_suggested` versus `confirmed`.

## Limits

- The model sees at most 18,000 characters of the source. A longer file is truncated and a gap is added.
- Scanned PDFs are not OCR’d.
- Chat will not approve an investigation. That stays in the review section.
- Causes are suggestions until a person confirms them. A high-confidence sentence from the model is not enough.
