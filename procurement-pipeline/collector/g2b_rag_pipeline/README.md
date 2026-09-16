# G2B RAG Pipeline

Standalone pipeline for collecting Korean Public Procurement Service (나라장터 / G2B) bid notices and attachments, parsing documents for RAG, and optionally recovering image-based PDFs with GPU OCR.

This project is **fully standalone**. It does **not** import or require the older `narajangteo_rag_ingest` project.

## Files

```text
g2b_rag_pipeline/
├─ run.sh
├─ config.toml
├─ run.py
├─ .env.example
├─ requirements.txt
├─ README.md
├─ CHECKLIST.md
└─ _engine/
   ├─ g2b_core.py
   ├─ g2b_month_pipeline.py
   └─ g2b_gpu_ocr.py
```

Most users only need to edit `config.toml` and run `run.sh`.

## Quick start

```bash
cd g2b_rag_pipeline
bash run.sh
```

On the first run, the launcher asks for the G2B / data.go.kr service key and stores it in `.env` as:

```env
NARA_API_KEY=YOUR_KEY
```

The normal execution order is:

```text
1. Fetch the entire target month from OpenAPI
2. Save filtered bid metadata
3. Download all attachment raw files
4. Parse documents with CPU multiprocessing
5. Rebuild manifest / quarantine / chunk_ready / summary
6. Run GPU OCR only for unresolved PDFs
7. Rebuild indexes again after OCR
```

The CPU parsing stage and GPU OCR stage are intentionally separated.

## Configuration

Edit `config.toml`.

Example:

```toml
[run]
year = 2026
month = 5
out = "./data"
resume = true
run_gpu_ocr = true
gpu_ocr_dpi = 160

[scope]
business_types = ["service", "goods", "construction", "foreign", "etc"]

[api_filters]
keyword = ""
demand_org = ""

[local_filters]
# min_budget = 100000000
# max_budget = 1000000000
contract_method = ""
bid_name_contains = ""
notice_org_contains = ""
demand_org_contains = ""
unknown_budget = "keep"

[attachment_filters]
doc_mode = "all"
eorder_fallback = false
duplicate_format_priority = [
  "hwpx", "docx", "hwp", "pdf", "txt", "xls", "xlsx", "zip"
]

[performance]
workers = 8
api_concurrency = 4
download_concurrency = 12
chunk_days = 15
page_size = 999
max_file_mb = 100
min_quality = 0.55
```

### Filter sections

`[scope]` selects which bid-notice API groups are queried.

`[api_filters]` contains filters intended for the OpenAPI request stage.

`[api_extra_params]` can hold additional PPSSrch query parameters supported by the API endpoint.

`[local_filters]` are applied after bid data has been fetched.

`[attachment_filters]` controls which attachments are collected and how multiple formats of the same logical document are prioritized.

`[performance]` controls API concurrency, download concurrency, parser worker count, file size limits, and quality thresholds.

## Run modes

### Normal one-click run

```bash
bash run.sh
```

This is the default mode.

It performs:

```text
fetch
→ download
→ CPU parse
→ GPU OCR if enabled and CUDA is available
→ final status
```

With `resume = true`, completed stages are reused where possible.

### `--cpu-only`

```bash
bash run.sh --cpu-only
```

Use this when you want to complete the normal OpenAPI collection, attachment download, and CPU parsing stages **without running GPU OCR**.

Behavior:

```text
fetch if needed
→ download if needed
→ CPU parse
→ rebuild chunk_ready / quarantine / summary
→ stop before OCR
```

Important details:

- It does **not** disable OpenAPI collection.
- It does **not** disable attachment downloading.
- It only disables the final GPU OCR stage.
- PDFs that still need OCR remain in `quarantine.jsonl`.
- CPU-parsed documents are still written to `parsed/`.
- RAG-ready CPU results are still written to `chunk_ready.jsonl`.
- It is safe to run OCR later with `--ocr-only`.

Typical use cases:

- You want the fastest possible first pass.
- Another GPU job is using the A5000.
- CUDA / EasyOCR is temporarily unavailable.
- You want to review the unresolved set before OCR.

After a CPU-only run, continue later with:

```bash
bash run.sh --ocr-only
```

### `--ocr-only`

```bash
bash run.sh --ocr-only
```

Use this only **after CPU parsing results already exist for the configured year/month**.

It skips the normal fetch, download, and CPU parse stages and tries GPU OCR only on the currently unresolved PDF candidates.

Required pre-existing state:

```text
data/YYYY-MM/
├─ download_manifest.jsonl
├─ parsed/
├─ quarantine.jsonl
└─ other CPU-stage outputs
```

Behavior:

```text
existing quarantine
→ find unresolved PDF candidates
→ read existing raw PDFs
→ EasyOCR + CUDA GPU
→ update parsed/<sha>.json
→ rebuild manifest / quarantine / chunk_ready / summary
```

Important details:

- It does **not** call the G2B OpenAPI.
- It does **not** redownload attachments.
- It does **not** rerun the general CPU parser.
- It only operates on existing unresolved PDF candidates.
- Non-PDF unresolved files remain unresolved.
- If CUDA is unavailable, OCR cannot proceed.
- The configured month in `config.toml` must match the existing data folder.

Typical use cases:

- A previous `--cpu-only` run finished successfully.
- OCR was interrupted and needs to be resumed.
- The GPU was unavailable earlier but is available now.
- You intentionally want CPU and GPU workloads at different times.

### `--settings`

```bash
bash run.sh --settings
```

Prints the effective configuration without running collection or parsing.

Use this before a large run to confirm:

- target year/month
- API scope
- filters
- attachment mode
- CPU worker count
- download concurrency
- quality threshold

### `--status`

```bash
bash run.sh --status
```

Displays the current status for the configured month without changing data.

## Resume behavior

Default:

```toml
resume = true
```

On a rerun for the same month:

- if `bids.jsonl` already exists, the fetch stage can be skipped
- if `download_manifest.jsonl` already exists, the download stage can be skipped
- successfully parsed documents are reused
- `failed`, `low_quality`, and `unsupported` parse caches are **not** treated as successful caches and are reparsed

This prevents the earlier failure mode where stale failed parse JSON files were reused forever.

If you change filters substantially for the same month, use a fresh output folder or back up/rename the old `data/YYYY-MM` folder before rerunning.

## HWP handling

The parser includes explicit HWP recovery logic:

```text
file named .hwp
→ detect whether it is actually legacy XLS
   → if OLE Workbook/Book: parse with xlrd
→ otherwise try HWP parsing
   → HWPLoader primary
   → olefile fallback
   → additional HWP fallback where available
→ if the same logical document also exists as PDF/DOCX/etc
   → select a successfully parsed alternate format
→ if all candidates fail
   → quarantine
```

DRM-protected, encrypted, severely damaged, or non-standard HWP files may remain unresolved.

## GPU OCR

GPU OCR is a fallback stage, not the primary parser.

It targets unresolved PDFs after CPU parsing.

Recommended hardware behavior:

```text
CPU parse first
→ GPU OCR second
```

This is intentional because PDF rasterization still consumes CPU, RAM, and disk I/O even when OCR recognition runs on CUDA.

The launcher does not force-reinstall `torch`, which helps preserve an already working CUDA PyTorch environment.

## Output layout

Each month is stored under:

```text
data/YYYY-MM/
```

Important outputs include:

```text
bids.jsonl
download_manifest.jsonl
raw/
parsed/
manifest.jsonl
quarantine.jsonl
chunk_ready.jsonl
summary.json
```

For RAG / Graph RAG, use:

```text
chunk_ready.jsonl
```

Do not blindly ingest every file under `parsed/`.

## Notes for another AI / maintainer

The orchestration entry point is:

```text
run.py
```

The shell wrapper is:

```text
run.sh
```

Internal implementation is under `_engine/`.

The intended architecture is:

```text
OpenAPI monthly fetch
→ complete raw attachment acquisition
→ CPU ProcessPool parsing
→ rebuild current indexes
→ unresolved-PDF GPU OCR
→ rebuild current indexes again
```

Key invariants:

- This project must remain independent from `narajangteo_ingest.py`.
- Only successful parsed caches above the quality threshold may be reused as successful cache.
- Failed / low-quality / unsupported caches must remain retryable.
- OCR must not trigger OpenAPI calls or attachment redownloads.
- `chunk_ready.jsonl` is the final RAG input index.
- Multiple representations of the same logical attachment group should contribute only the selected successful representation to `chunk_ready.jsonl`.
