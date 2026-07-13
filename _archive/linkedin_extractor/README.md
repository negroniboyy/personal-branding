# LinkedIn extractor (archived 2026-07-09)

One-time CLI utilities from the reference era, archived per masterplan v4.0 §1 item #4
(no imports from any live route/module).

- `extract_linkedin.py` — CLI that extracts LinkedIn post frameworks from `.txt` reference files.
- `llm_client.py` — its LLM helper (imported by the above).

**To restore:** move both files back to `frameworks/linkedin_frameworks/`. They still expect
their prompt at `frameworks/linkedin_frameworks/prompts/extract_linkedin.txt` and reference/output
data under `frameworks/linkedin_frameworks/{references,frameworks,schema.yaml}` — all left in place.
