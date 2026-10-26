# Uncertainty-aware and trustworthy LLMs in education: systematic review materials

Supplementary materials for:

> M. Adnan, M. I. Uddin and M. H. Hassan, "Knowing When the Model Doesn't Know: A Systematic Review of Uncertainty-Aware and Trustworthy Large Language Models in Education," submitted to *IEEE Transactions on Learning Technologies*.

The repository contains the protocol, search strings and logs, all screening and eligibility decisions, the coded data for the 305 included studies, and the code used for searching, full-text retrieval and the figures. It follows PRISMA 2020 and PRISMA-S.

## Study flow (summary)

| Stage | n |
|---|---|
| Records identified (OpenAlex 4,898; arXiv 587; ERIC 103) | 5,588 |
| Records screened on title and abstract (after de-duplication and an automated term check) | 3,769 |
| Excluded at title/abstract stage | 3,356 (11 reinstated after human verification) |
| Reports sought (database search) | 424 |
| Citation-search records screened / sought | 474 / 60 |
| Reports assessed (full text 193; abstract only 236) | 429 |
| Awaiting classification (no full text or abstract) | 55 |
| **Studies included** (database 260; citation searching 45) | **305** |

## Contents

| Folder | Files | Description |
|---|---|---|
| `protocol/` | `Survey_Protocol_v1.0.docx`, `Survey_Protocol_v1.1_amendments.docx` | Review protocol written before screening, and the amendments made afterwards |
| `search/` | `search_strings.md`, `search_log_api.csv`, `records_deduplicated.csv`, `records_excluded_automation_check.csv` | Search strings, API search log (date, query, hits), the 3,769 screened records and the records removed by the automated three-block term check (metadata only) |
| `screening/` | `title_abstract_decisions.csv`, `human_verification_of_exclusions.csv`, `citation_search_decisions.csv` | Every title/abstract decision with its reason code and the open-model pre-screen probability; the first author's verification of a stratified sample of exclusions and how disagreements were resolved; decisions for citation-search records |
| `fulltext/` | `reports_sought.csv`, `assessment_basis.csv` | Reports sought for retrieval and whether each was assessed on full text, on its abstract, or is awaiting classification |
| `extraction/` | `coded_studies.csv`, `Data_Extraction_Coding_Sheet.xlsx`, `human_coding_check_40.csv` | Eligibility decision and coding for every assessed report (codebook in the spreadsheet), and the first author's check of a random sample of 40 coded studies |
| `code/search/` | `survey_pipeline.py/.ipynb` | Harvesting from OpenAlex, arXiv and ERIC, de-duplication and automated term check |
| `code/retrieval/` | `fulltext_pipeline.py/.ipynb`, `fulltext_round2_snowball.ipynb`, `fetch_missing_abstracts.ipynb` | Open-access full-text retrieval, text extraction, backward/forward citation searching, and abstract look-up |
| `analysis/` | `make_figures.py`, `prisma.py`, `taxonomy.py`, `style.py`, `prisma_numbers.json` | Code that produces all figures in the article from the coded data |
| `figures/` | PDF and PNG | Figures as they appear in the article |

## Codes used in `coded_studies.csv`

- **Exclusion reasons:** E1 not an LLM; E2 not an educational setting; E3 no uncertainty or reliability focus; E4 opinion or no method; E5 not English; E6 duplicate; E9 secondary study (review).
- **Task:** SCO scoring and grading; FB feedback; TQA tutoring and question answering; DIAG error diagnosis; GEN item and content generation; LA learning analytics and coding of educational data; ADV advising and administration; USE student or teacher use of general-purpose LLMs.
- **Uncertainty signal (`uq_methods`):** VC verbalised confidence; TP token probability; SC sampling consistency; EN ensemble or multi-LLM disagreement; CP conformal prediction; CAL calibration or learned confidence; RV retrieval or verification; HR comparison with humans or another reference only; UT user-side trust or reliance.
- **Action:** DISP shown to user; ABST abstain; DEFER route to a human; SEL selective automation; ASK clarifying question; VER verify or regenerate; WARN warning; NONE measured only.
- **Technical evaluation:** AGR agreement; ACC accuracy or error; CALIB calibration; DISC discrimination; SELR coverage-risk; HALL hallucination rate; ROB robustness. **Human evaluation:** TRUST, RELIANCE, WORKLOAD, PERCEPTION.
- **Other columns:** `basis` (full text or abstract), `edu_level` (K12, HE, HP health professions, PRO, MIX, NS not specified), `setting` (REAL course, EXP experiment, OFF offline data, SIM simulation, DEMO prototype), `model_access` (C closed, O open, B both, U not reported), `adaptation` (P prompting, PR prompting plus retrieval, FT fine-tuning), `quality_0_8` (adapted MMAT; full-text studies only).

## Reproducing the figures

```bash
pip install pandas numpy matplotlib openpyxl
python analysis/make_figures.py   # trends, heatmap, flow and evidence figures
python analysis/prisma.py         # PRISMA flow diagram
python analysis/taxonomy.py       # framework figure
```

## Use of AI tools

AI tools were used in this review and are reported in the article. Claude (Anthropic) made the title and abstract screening decisions and drafted the eligibility decisions and data extraction; Qwen2.5-7B-Instruct produced an independent inclusion probability for every screened record. The first author verified a stratified sample of 170 exclusions (agreement 90.6%) and a random sample of 40 coded studies (agreement 82.5 to 92.5% across fields). Disagreements and their resolution are recorded in the files above.

## Copyright

Abstracts and full texts of the included studies are not redistributed; records are identified by title and DOI. Data are released under CC BY 4.0 and code under the MIT License.
