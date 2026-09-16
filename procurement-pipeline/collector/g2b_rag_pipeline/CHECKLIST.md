# CHECKLIST

This file documents the intended behavior of the standalone G2B RAG pipeline so that a human or another AI can verify future modifications.

## Project structure

- [x] Project folder name is `g2b_rag_pipeline`
- [x] All user-facing filenames are English
- [x] Main launcher is `run.sh`
- [x] Main orchestration entry point is `run.py`
- [x] User configuration is centralized in `config.toml`
- [x] Implementation details are hidden under `_engine/`
- [x] No import or runtime dependency on the older `narajangteo_ingest.py`

## One-click behavior

- [x] `bash run.sh` performs the normal end-to-end pipeline
- [x] First run asks for `NARA_API_KEY` if `.env` is missing
- [x] API key is stored separately in `.env`
- [x] `config.toml` contains date, filters, and performance settings
- [x] Normal order is fetch → download → CPU parse → optional GPU OCR
- [x] CPU parse and GPU OCR are not run concurrently by default

## OpenAPI collection

- [x] Year/month are configurable
- [x] Service / goods / construction / foreign / etc API groups are configurable
- [x] API-stage keyword filter is configurable
- [x] API-stage demand organization filter is configurable
- [x] Additional PPSSrch query parameters can be supplied
- [x] Monthly bids are fetched before CPU parsing starts
- [x] Bid metadata is saved before attachment parsing

## Local filters

- [x] Minimum budget filter is configurable
- [x] Maximum budget filter is configurable
- [x] Contract method filter is configurable
- [x] Bid-name substring filter is configurable
- [x] Notice-organization substring filter is configurable
- [x] Demand-organization substring filter is configurable
- [x] Unknown budget behavior is configurable

## Attachment acquisition

- [x] Attachment mode supports `all` and `relevant`
- [x] Attachment downloads are concurrent
- [x] Raw files are stored before CPU parsing
- [x] Same bid + same URL duplicates are removed
- [x] Multiple formats of the same logical document are grouped
- [x] Representation priority is configurable

## CPU parsing

- [x] CPU parsing uses multiprocessing
- [x] Default worker count is suitable for the user's 20-logical-CPU workstation
- [x] OCR is excluded from the general CPU parsing stage
- [x] Successful parsed cache can be reused
- [x] Failed cache is retryable
- [x] Low-quality cache is retryable
- [x] Unsupported cache is retryable
- [x] Current indexes are rebuilt from current parse state
- [x] `summary.json` reflects current state, not stale historical failure totals

## HWP recovery

- [x] Detect `.hwp` files that are actually legacy XLS
- [x] Legacy OLE Workbook/Book files use `xlrd`
- [x] HWP primary path uses HWPLoader
- [x] HWP fallback uses `olefile`
- [x] Alternate successful PDF/DOCX/etc representation can be selected
- [x] Completely unresolved groups remain in quarantine

## GPU OCR

- [x] GPU OCR is implemented in a separate engine module
- [x] OCR targets unresolved PDFs after CPU parsing
- [x] OCR does not call the G2B OpenAPI
- [x] OCR does not redownload attachments
- [x] OCR does not rerun the general CPU parser
- [x] OCR updates parsed output and rebuilds final indexes
- [x] CUDA availability is checked before OCR execution
- [x] Existing CUDA PyTorch installation is not forcibly replaced

## Run mode semantics

### `bash run.sh`

- [x] Normal end-to-end execution
- [x] Fetches if needed
- [x] Downloads if needed
- [x] Runs CPU parsing
- [x] Runs GPU OCR when enabled and available
- [x] Prints final status

### `bash run.sh --cpu-only`

- [x] Still performs fetch if needed
- [x] Still performs attachment download if needed
- [x] Still performs CPU general parsing
- [x] Rebuilds `chunk_ready.jsonl`, `quarantine.jsonl`, and `summary.json`
- [x] Stops before GPU OCR
- [x] Leaves unresolved OCR candidates in quarantine
- [x] Can be followed later by `--ocr-only`

### `bash run.sh --ocr-only`

- [x] Assumes CPU-stage outputs already exist
- [x] Skips OpenAPI fetch
- [x] Skips attachment download
- [x] Skips general CPU parsing
- [x] Uses existing raw PDFs and current quarantine state
- [x] Runs only unresolved-PDF GPU OCR
- [x] Rebuilds indexes after OCR
- [x] Leaves unresolved non-PDF documents untouched

### `bash run.sh --settings`

- [x] Shows effective settings without starting the pipeline

### `bash run.sh --status`

- [x] Shows current month status without modifying data

## RAG output contract

- [x] `chunk_ready.jsonl` is the intended RAG / Graph RAG input
- [x] `parsed/` is a cache/store, not the final RAG selection index
- [x] Failed / low-quality / unsupported documents are excluded from `chunk_ready.jsonl`
- [x] Multiple formats of one logical document contribute only the selected successful representation

## Future modification rule

If another AI modifies this project, it should preserve the following invariants unless explicitly instructed otherwise:

1. Keep the project standalone.
2. Keep fetch/download/CPU parse/OCR as distinct stages.
3. Never treat failed parse cache as successful cache.
4. Never make OCR call the OpenAPI or redownload attachments.
5. Keep `chunk_ready.jsonl` as the final RAG input contract.
6. Keep `--cpu-only` and `--ocr-only` semantics exactly as documented above.
