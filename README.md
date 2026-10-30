# RoadEnv: a tool-use eval environment over a real, messy government report

**What it is.** A small, bounded evaluation environment for LLM agents. Each episode is one question about
India's official *Road Accidents in India 2024* report (Ministry of Road Transport & Highways, 266 pages,
published June 2026). The agent has a budget of 10 tool calls (`search`, `read_page`, `calculate`, `submit`) and is scored
by a deterministic grader. Built by Pradeep Rathore as proof of work for an Environment Engineering role.

**Why this document.** It is the kind of source enterprise agents actually face: Indian digit grouping
(4,87,707), tables split across pages with no title on the continuation page, wrapped row labels, `NA`
cells with footnotes, 102 annexure pages that are **images with no text layer** (some rotated), and a
few internal inconsistencies. An agent that does well here has to read tables, not just retrieve text.

## Layout
```
make_tasks.py        30 tasks with hand-verified ground truth -> tasks.jsonl
roadenv/env.py       environment: corpus, BM25 search, tools, step budget, episode trace
roadenv/grader.py    deterministic grader (Indian number parsing, tolerance, refusal logic, citation check)
agents/baselines.py  refuse_all, table_reader (retrieve + regex), table_reader_oracle (given the gold page)
agents/llm_agent.py  OpenAI-compatible ReAct agent (plug-in; not run, no API key was available)
run_eval.py          runs agents x corpora -> results/*.json, results/summary.md
retrieval_check.py   recall@k of the search tool -> results/retrieval.json
test_grader.py       gold answers must score 1.0; known-wrong answers must fail
data/                page-level text layer (266 pages) + OCR of the 102 image-only pages; fetch_report.sh rebuilds both
```
Run: `pip install rank_bm25 && python test_grader.py && python run_eval.py && python retrieval_check.py`
(runs in under a second; no network needed).

## Task set (30)
| category | n | what it tests |
|---|---|---|
| lookup | 13 | one cell or one sentence (state, city, national figures) |
| messy | 4 | `NA` cell + footnote (Ladakh 2020), NA-shifted columns, wrapped row label, -100% edge case |
| units | 1 | answer in lakh |
| derived | 4 | sums, counts across 36 rows, shares, arg-max |
| spec | 3 | where the "right" answer depends on a convention the grader must pin (see findings) |
| image_only | 2 | value exists only in an image-only annexure page |
| unanswerable | 3 | not in the report, including a near-miss distractor; correct = `not_available` |

Ground truth was read off the PDF by hand; each task stores the PDF page and a line-level evidence regex.
A citation counts only if the cited page contains a line matching that regex.
Reward = correct × (0.8 + 0.2 × valid citation).

## Results (baselines only, real runs)
| agent | corpus | correct | lookup | messy | derived | spec | image-only | unanswerable |
|---|---|---|---|---|---|---|---|---|
| refuse_all | text | 4/30 (13%) | 0/13 | 1/4 | 0/4 | 0/3 | 0/2 | 3/3 |
| table_reader | text | 4/30 (13%) | 0/13 | 2/4 | 0/4 | 0/3 | 0/2 | 2/3 |
| table_reader | text+OCR | 5/30 (17%) | 1/13 | 2/4 | 0/4 | 0/3 | 0/2 | 2/3 |
| table_reader_oracle (given gold page) | text | 12/30 (40%) | 8/13 | 2/4 | 0/4 | 0/3 | 0/2 | 2/3 |

Search tool recall (gold page in top k, 26 answerable tasks): text corpus R@1 27%, R@3 38%, R@10 69%;
text+OCR R@3 42%, R@10 54%.

## Findings
1. **Retrieval is the bottleneck, not extraction.** The same naive extractor goes from 4/30 to 12/30
   when handed the right page. The state-wise master tables (Table 5.1, 5.6) are rarely retrieved:
   each state name appears once on them but also in prose elsewhere, so page-level BM25 prefers prose.
   Kerala 2022, Rajasthan 2023 deaths and Goa 2024 deaths never reach the top 10.
2. **Adding OCR made search worse.** Blending OCR of the 102 annexure pages into one index cut R@10 from
   69% to 54%: state names now appear on ~100 more pages and stop discriminating. Image-only tasks stayed
   0/2. OCR should go in a separate, table-aware index keyed by annexure title.
3. **OCR silently corrupts cells.** Annexure 5 (fatal accidents by state) has no text layer; tesseract reads
   D&N Haveli and Daman & Diu's 2023 value as "2B" (the image says 73).
4. **The report has a printed arithmetic error.** Table 5.6 gives Goa's 2024 change in deaths as −1.28%;
   its own counts (290 → 286) give −1.38%. Task T25 rewards the computed value, so a copy-the-cell agent fails.
5. **Conventions must be pinned.** The report's "1,336 accidents per day" divides 4,87,707 by 365, but 2024
   had 366 days (→ 1,333). T23 asks for the report's figure, T24 for the computed one; without that split the
   grader would mark one of two defensible answers wrong.
6. **Year words lure hallucinations.** Asked for accidents "in 2025" (not covered), the baseline answered from a
   page citing *World Road Statistics, 2025*.
7. **My own bug, caught by the env.** My first extractor lowercased rows, so Ladakh's `NA` cell vanished and
   it returned 236 (the 2021 value) for 2020: exactly the NA-shift trap T14/T15 were written for. Fixed;
   the v0 scores are kept in `results/summary_v0_no_stopwords_buggy_baseline.md`. A stopword-free search tool
   also ranked a short chart page (PDF p.99) first for 7 of 30 questions, on words like "report" and "many"; stopwords were added.

The internal totals do reconcile: the 36 state/UT rows of Tables 5.1 and 5.6 sum exactly to the All-India
totals for every year 2020–2024 (checked with a script during build).

## Limits (honest)
- No LLM was run here (no API key in the build sandbox). `agents/llm_agent.py` is ready; the numbers above are
  baselines that calibrate the environment, not a model benchmark.
- 30 tasks over one document: enough to expose failure modes, too few for tight confidence intervals.
- Ground truth is single-annotator (me). Image-only answers were checked visually on the rendered page.
- OCR text in `data/pages_ocr.jsonl` was produced at 200 dpi (pages 164–200) and 170 dpi (201–265).

Source PDF: https://morth.gov.in/backend/documents/uploaded/1781177676_V1gUW8tJWT.pdf
(sha256 b45b0e4d…64be69b2).
