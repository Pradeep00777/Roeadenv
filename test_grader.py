#!/usr/bin/env python3
"""Sanity checks: (1) gold answers + first gold page score 1.0 on every task; (2) known-bad answers fail."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roadenv.env import load_tasks, load_pages
from roadenv.grader import grade, parse_number
pages = load_pages("text+ocr"); bad = 0
for t in load_tasks():
    sub = {"answer": t["answer"], "status": "not_available" if t["type"] == "na" else "answered",
           "citation_page": t["pages"][0] if t["pages"] else None}
    r = grade(t, sub, pages)
    if r["reward"] != 1.0:
        bad += 1; print("GOLD FAILS", t["id"], r)
assert parse_number("4,87,707") == 487707 and parse_number("4.71 lakh") == 471000 and parse_number("-1.38%") == -1.38
T = {t["id"]: t for t in load_tasks()}
assert grade(T["T25"], {"answer": -1.28, "status": "answered", "citation_page": 110}, pages)["correct"] is False
assert grade(T["T14"], {"answer": 236, "status": "answered"}, pages)["outcome"] == "hallucinated"
assert grade(T["T02"], {"answer": 43910, "status": "answered", "citation_page": 34}, pages)["reward"] == 0.8
print("gold failures:", bad, "| negative checks passed")
