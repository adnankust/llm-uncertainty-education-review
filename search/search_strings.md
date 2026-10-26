# Search strings (version 2): uncertainty-aware and trustworthy LLMs in education (systematic review)

- **Search fields:** title, abstract and keywords.
- **Years:** 2020 to the date of the search.
- **Language:** English.
- **Record each search in `search_log.csv`:** the date, the exact string you pasted, the filters, the number of hits and the number of records exported. PRISMA 2020 and PRISMA-S require this record.
- **Run all searches within the same week** so that the database snapshots match.

The three term blocks are:

- **A:** large language models
- **B:** uncertainty and trust
- **C:** educational setting

`*` is the truncation (wildcard) symbol.

---

## 1. Scopus (Advanced search)

```
TITLE-ABS-KEY ( "large language model*" OR llm* OR "generative AI" OR "generative artificial intelligence"
   OR gpt* OR chatgpt OR "pretrained language model*" OR "pre-trained language model*" )
AND TITLE-ABS-KEY ( uncertaint* OR "confidence score*" OR "confidence estimat*" OR "model confidence"
   OR "confidence calibration" OR "verbali?ed confidence" OR overconfiden* OR calibrat* OR miscalibrat*
   OR conformal OR abstain* OR abstention OR "selective prediction" OR "selective classification" OR deferral
   OR "learning to defer" OR "human-in-the-loop" OR "teacher-in-the-loop" OR "hallucination detection"
   OR "hallucination rate*" OR "hallucination mitigation" OR "detect* hallucination*" OR "factual consistency"
   OR "trust calibration" OR "appropriate reliance" )
AND TITLE-ABS-KEY ( educat* OR student* OR learner* OR teacher* OR tutor* OR "automated scoring" OR grading
   OR "automated feedback" OR "formative assessment*" OR "summative assessment*" OR "automated assessment*"
   OR "student assessment*" OR "educational assessment*" OR classroom* OR mooc* OR "learning analytics" )
AND NOT TITLE-ABS-KEY ( "knowledge distillation" OR "teacher-student" )
AND PUBYEAR > 2019 AND ( LIMIT-TO ( LANGUAGE , "English" ) )
```

**Export:**
- Click Export, then CSV.
- Tick **all information**: citation information, bibliographical information, abstract and keywords.
- Name the file `scopus_export.csv`.

## 2. Web of Science Core Collection (Advanced search)

```
TS=( "large language model*" OR LLM* OR "generative AI" OR "generative artificial intelligence" OR GPT*
   OR ChatGPT OR "pretrained language model*" OR "pre-trained language model*" )
AND TS=( uncertaint* OR "confidence score*" OR "confidence estimat*" OR "model confidence" OR "confidence calibration"
   OR "verbali?ed confidence" OR overconfiden* OR calibrat* OR miscalibrat* OR conformal OR abstain* OR abstention
   OR "selective prediction" OR "selective classification" OR deferral OR "learning to defer" OR "human-in-the-loop"
   OR "teacher-in-the-loop" OR "hallucination detection" OR "hallucination rate*" OR "hallucination mitigation"
   OR "detect* hallucination*" OR "factual consistency" OR "trust calibration" OR "appropriate reliance" )
AND TS=( educat* OR student* OR learner* OR teacher* OR tutor* OR "automated scoring" OR grading OR "automated feedback"
   OR "formative assessment*" OR "summative assessment*" OR "automated assessment*" OR "student assessment*"
   OR "educational assessment*" OR classroom* OR MOOC* OR "learning analytics" )
NOT TS=( "knowledge distillation" OR "teacher-student" )
```

**Filters:** Publication years 2020 to now; Language: English.

**Export:**
- Choose Export, then **Tab delimited file**, record content **Full Record**.
- Web of Science allows 1,000 records per export, so export 1–1000, 1001–2000 and so on.
- Name the files `wos_1.txt`, `wos_2.txt` and so on.

## 3. IEEE Xplore (Command search)

IEEE Xplore limits the number of terms per query, so run three searches, one for each part of block B. Export all three; the pipeline removes the duplicates.

- **Shared parts:** blocks A and C stay the same in every run.
  - **A:** `("All Metadata":"large language model*" OR "All Metadata":LLM* OR "All Metadata":"generative AI" OR "All Metadata":ChatGPT OR "All Metadata":GPT*)`
  - **C:** `("All Metadata":educat* OR "All Metadata":student* OR "All Metadata":learner* OR "All Metadata":teacher* OR "All Metadata":tutor* OR "All Metadata":grading OR "All Metadata":classroom*)`
- **Run 1:** `A AND ("All Metadata":uncertaint* OR "All Metadata":calibrat* OR "All Metadata":conformal OR "All Metadata":"confidence estimation" OR "All Metadata":overconfiden*) AND C`
- **Run 2:** `A AND ("All Metadata":abstain* OR "All Metadata":abstention OR "All Metadata":"selective prediction" OR "All Metadata":deferral OR "All Metadata":"human-in-the-loop") AND C`
- **Run 3:** `A AND ("All Metadata":"hallucination detection" OR "All Metadata":"hallucination rate*" OR "All Metadata":"factual consistency" OR "All Metadata":"trust calibration" OR "All Metadata":"appropriate reliance") AND C`

**Filters:** Year 2020 to now.

**Export:** Click Export, then CSV. Name the files `ieee_1.csv`, `ieee_2.csv` and `ieee_3.csv`.

## 4. ACM Digital Library (Advanced search, Search within: Abstract)

- **Block A:** `"large language model" OR "large language models" OR LLM OR LLMs OR "generative AI" OR ChatGPT OR GPT`
- **Block B:** `uncertainty OR "confidence estimation" OR "confidence score" OR calibration OR calibrated OR conformal OR abstain OR abstention OR "selective prediction" OR deferral OR "human-in-the-loop" OR "hallucination detection" OR "factual consistency" OR "trust calibration" OR "appropriate reliance"`
- **Block C:** `education OR educational OR student OR students OR learner OR teacher OR tutoring OR grading OR classroom OR MOOC`

Join the three blocks with AND.

**Filters:** Publication date from 2020.

**Export:**
- Select all results, then click **Export Citations** and choose **BibTeX**.
- Name the file `acm_export.bib`.

**Note:** whatever each database matches, the notebook keeps only records whose own title or abstract contains all three term blocks. This automated check is reported as a separate step in the PRISMA diagram, so the five sources are filtered consistently.

## 5. ERIC, arXiv and OpenAlex (automatic)

The Kaggle notebook searches **ERIC**, **arXiv** and **OpenAlex** through their free public APIs, using the same term blocks with explicit word forms (APIs do not accept `*`). No manual export is needed.

If you also want the ERIC website version, search eric.ed.gov with blocks A AND B and export the results as RIS to `eric.ris`.

---

## Adding the exports to Kaggle

1. Put all exported files in one folder and create a Kaggle dataset from it (for example `llm-uncertainty-survey-exports`).
2. In the notebook, choose **Add Data** and select that dataset. Set **Internet ON** (for the APIs) and **GPU T4 x2** (for the optional AI pre-screen).
3. Run the notebook. Send me the output `survey_screening_<date>.zip`.

The file names must contain `scopus`, `wos`/`savedrecs`, `ieee`, `acm` or `eric`, so the pipeline can label each source correctly for the PRISMA diagram.
