#!/usr/bin/env python3
"""Recall@k of the env's BM25 search tool: is a gold page in the top k for each answerable task?"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roadenv.env import RoadEnv, load_tasks
from roadenv.grader import citation_ok
out = {}
for v in ["text", "text+ocr"]:
    env = RoadEnv(v); rows = []
    for t in load_tasks():
        if t["type"] == "na": continue
        env.reset(t)
        hits = [h["page"] for h in env.search(t["question"], 10)]
        gold = [p for p in hits if citation_ok(t, p, env.cite_pages)]
        rank = hits.index(gold[0]) + 1 if gold else None
        rows.append((t["id"], t["category"], rank))
    n = len(rows)
    out[v] = {f"recall@{k}": sum(1 for r in rows if r[2] and r[2] <= k) / n for k in (1, 3, 10)}
    out[v]["ranks"] = {i: r for i, _, r in rows}
    print(v, {k: round(x, 2) for k, x in out[v].items() if k != "ranks"})
json.dump(out, open("results/retrieval.json", "w"), indent=1)
