#!/usr/bin/env python3
"""Writes tasks.jsonl: 28 questions over MoRTH 'Road Accidents in India 2024' with hand-verified ground truth.

Every answer was read off the report (PDF page given in `pages`) by a person, not generated.
`evidence` is a line-level regex: a citation is valid if the cited page has a line matching it
(searched in the text layer and, for image-only pages, the OCR layer). `extra_pages` are accepted
citations the regex cannot catch (e.g. an OCR misread on the right page).

answer types: int (exact after normalising Indian digit grouping / lakh), float (abs tolerance),
str (normalised, aliases allowed), na (correct behaviour is status="not_available").
"""
import json

T = []
def t(id, cat, q, typ, ans, pages, evidence=None, tol=None, aliases=None, extra_pages=None, note=""):
    T.append(dict(id=id, category=cat, question=q, type=typ, answer=ans, tol=tol, aliases=aliases or [],
                  pages=pages, evidence=evidence, extra_pages=extra_pages or [], note=note))

# --- direct lookups in a table (text layer) -------------------------------------------------
t("T01", "lookup", "How many road accidents were reported in India in calendar year 2024?", "int", 487707,
  [34, 35], r"4,87,707")
t("T02", "lookup", "How many road accidents did Kerala report in 2022?", "int", 43910,
  [105], r"Kerala\s+[\d,]+\s+[\d,]+\s+43,910", note="Kerala row has five year columns; picking the wrong one is the trap.")
t("T03", "lookup", "How many road accidents did Telangana report in 2024?", "int", 25986,
  [105], r"Telangana\s+.*25,986")
t("T04", "lookup", "What was Rajasthan's rank among States/UTs by total number of road accidents in 2024?", "int", 8,
  [105], r"Rajasthan\s+19,114", note="Rank columns sit after the change columns; 2023 rank was 7.")
t("T05", "lookup", "How many persons were killed in road accidents in Rajasthan in 2023?", "int", 11762,
  [110, 111], r"Rajasthan\s+.*11,762")
t("T06", "lookup", "How many persons were killed in road accidents in Goa in 2024?", "int", 286,
  [110], r"Goa\s+223\s+226", note="Row is on a 'table contd...' page that has no table title, so title-based retrieval misses it.")
t("T07", "lookup", "How many persons killed in road accidents in 2024 were not wearing a helmet?", "int", 54122,
  [77], r"54,122")
t("T08", "lookup", "What percentage of road accident deaths in 2024 were attributed to over-speeding?", "float", 70.28,
  [75], r"Over-speeding.*1,24,522", tol=0.01, note="Accidents share is 70.74, deaths share 70.28: same row, adjacent cells.")
t("T09", "lookup", "How many persons were killed in road accidents in Delhi in 2024?", "int", 1551,
  [110, 113, 120], r"Delhi\s+.*1,551")
t("T10", "lookup", "How many road accidents were recorded in Jaipur (million-plus city) in 2024?", "int", 3115,
  [120, 121], r"Jaipur\s+.*3,115")
t("T11", "lookup", "What was the combined share (%) of the top 10 States in road accident deaths in 2024?", "float", 73.8,
  [111], r"73\.8", tol=0.05)
t("T12", "lookup", "Which State recorded the highest number of road accident deaths in 2024?", "str", "Uttar Pradesh",
  [35, 111], r"Uttar Pradesh|Uttar\s+Pradesh", aliases=["UP"])
t("T13", "lookup", "How many fatal road accidents were there in India in 2024?", "int", 164378,
  [28, 36], r"1,64,378")

# --- messy-layout traps ---------------------------------------------------------------------
t("T14", "messy", "How many road accidents did Ladakh report in 2020?", "na", None,
  [105], r"Ladakh\s+NA", note="Cell is 'NA'; footnote '# Includes Ladakh in 2020' on Jammu and Kashmir. Correct: not available separately.")
t("T15", "messy", "How many road accidents did Ladakh report in 2021?", "int", 236,
  [105], r"Ladakh\s+NA\s+236", note="An extractor that drops 'NA' shifts every Ladakh column left by one.")
t("T16", "messy", "By what percentage did road accidents in Lakshadweep change in 2024 compared with 2023?", "float", -100.0,
  [105], r"Lakshadweep\s+1\s+4", tol=0.05, note="1 -> 0 accidents.")
t("T17", "messy", "How many road accidents did Andaman & Nicobar Islands report in 2024?", "int", 135,
  [105], r"^\s*29\s+141\s+115", note="State name wraps onto two lines; the numbers sit on a line with no name.")
t("T18", "units", "How many persons were injured in road accidents in India in 2024, expressed in lakh (two decimals)?", "float", 4.71,
  [34, 35], r"4,71,441|4\.71", tol=0.005)

# --- derived / multi-hop ----------------------------------------------------------------------
t("T19", "derived", "What was the combined number of road accidents in 2024 in Rajasthan, Gujarat and Madhya Pradesh?", "int", 97095,
  [105], r"Madhya Pradesh\s+45,266", note="24,838 + 15,588 + 56,669.")
t("T20", "derived", "How many of the 36 States/UTs recorded fewer road accidents in 2024 than in 2023?", "int", 20,
  [105], r"Total \(All India\)", note="Count of negative 'absolute change' cells in Table 5.1.")
t("T21", "derived", "Kerala's 2024 road accidents as a percentage of the all-India total (two decimals)?", "float", 10.01,
  [105, 35], r"Kerala\s+.*48,834", tol=0.02, note="48,834 / 4,87,707. Report text rounds to 10.0%.")
t("T22", "derived", "Which State/UT had the largest absolute increase in road accidents in 2024 over 2023?", "str", "Telangana",
  [105], r"Telangana\s+.*3,083", note="+3,083.")

# --- specification ambiguity / document errors ------------------------------------------------
t("T23", "spec", "According to the report, about how many road accidents occurred per day on average in 2024?", "int", 1336,
  [34], r"1,336")
t("T24", "spec", "Using the 2024 all-India accident total and the actual number of days in calendar year 2024, what is the average number of accidents per day (nearest whole number)?", "int", 1333,
  [34, 35], r"4,87,707", note="2024 is a leap year: 4,87,707/366 = 1,332.5. The report's '1,336' divides by 365.")
t("T25", "spec", "Using the 2023 and 2024 death counts printed for Goa in Table 5.6, compute the percentage change in 2024 over 2023 (two decimals).", "float", -1.38,
  [110], r"Goa\s+223\s+226", tol=0.005, note="290 -> 286 is -1.38%; the table's own % column prints -1.28.")

# --- answer exists only in an image-only annexure page ---------------------------------------
t("T26", "image_only", "How many fatal road accidents were there in Rajasthan in 2024 (State/UT-wise, Annexure 5)?", "int", 10775,
  [170], r"Rajasthan\s+9,055", note="Annexure pages have no text layer; verified visually on PDF page 170.")
t("T27", "image_only", "How many fatal road accidents were there in Dadra & Nagar Haveli and Daman & Diu in 2023 (Annexure 5)?", "int", 73,
  [170], r"Haveli.*\s71\s+88", extra_pages=[170], note="Verified visually as 73; tesseract reads the cell as '2B'.")

# --- not answerable from this document ------------------------------------------------------
t("T28", "unanswerable", "How many road accidents were reported in India in 2025?", "na", None, [], None,
  note="Report covers calendar 2024; '2025' appears only in source citations.")
t("T29", "unanswerable", "What total compensation (in rupees) was paid to road accident victims in Rajasthan in 2024?", "na", None, [], None,
  note="Near-miss distractor: the report quotes per-victim hit-and-run compensation amounts (p40, p155) but no totals paid.")
t("T30", "unanswerable", "How many road accidents occurred in Rajasthan in 2019?", "na", None, [], None,
  note="State tables start at 2020 (Table 5.1) or 2021 (Annexures); 2019 appears only as an all-India figure in Chart 1.1.")

if __name__ == "__main__":
    with open("tasks.jsonl", "w") as f:
        for x in T:
            f.write(json.dumps(x) + "\n")
    print(len(T), "tasks written")
