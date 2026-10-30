#!/usr/bin/env python3
"""Run agents x corpus variants over all tasks; write results/*.json and results/summary.md.

  python run_eval.py                         # all non-LLM baselines, both corpora
  python run_eval.py --agent llm --variant text   # needs LLM_API_KEY etc. (see agents/llm_agent.py)
"""
import argparse, collections, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roadenv.env import RoadEnv, load_tasks
from agents.baselines import AGENTS

def run(agent_name, variant):
    if agent_name == "llm":
        from agents.llm_agent import llm_agent as fn
    else:
        fn = AGENTS[agent_name]
    env, out = RoadEnv(variant), []
    for t in load_tasks():
        try:
            r = fn(env, t)
        except RuntimeError as e:  # step budget exhausted
            r = {"id": t["id"], "category": t["category"], "correct": False, "citation_ok": False,
                 "reward": 0.0, "outcome": "budget_exhausted", "submitted": None, "expected": t["answer"]}
        out.append(r)
    return out

def summarise(res):
    n = len(res)
    by_cat = collections.defaultdict(lambda: [0, 0])
    for r in res:
        by_cat[r["category"]][0] += r["correct"]; by_cat[r["category"]][1] += 1
    return {"n": n, "accuracy": sum(r["correct"] for r in res) / n,
            "mean_reward": sum(r["reward"] for r in res) / n,
            "cited_when_correct": sum(r["citation_ok"] for r in res) / max(1, sum(r["correct"] for r in res)),
            "outcomes": dict(collections.Counter(r["outcome"] for r in res)),
            "by_category": {k: f"{a}/{b}" for k, (a, b) in sorted(by_cat.items())}}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", nargs="*", default=list(AGENTS))
    ap.add_argument("--variant", nargs="*", default=["text", "text+ocr"])
    a = ap.parse_args()
    os.makedirs("results", exist_ok=True)
    rows = []
    for ag in a.agent:
        for v in a.variant:
            res = run(ag, v)
            s = summarise(res)
            json.dump({"agent": ag, "variant": v, "summary": s, "results": res},
                      open(f"results/{ag}__{v.replace('+', '_')}.json", "w"), indent=1, default=str)
            rows.append((ag, v, s))
            print(f"{ag:22s} {v:9s} acc={s['accuracy']:.2f} reward={s['mean_reward']:.2f} {s['outcomes']}")
    cats = sorted({c for _, _, s in rows for c in s["by_category"]})
    md = ["| agent | corpus | accuracy | mean reward | " + " | ".join(cats) + " |",
          "|---|---|---|---|" + "---|" * len(cats)]
    for ag, v, s in rows:
        md.append(f"| {ag} | {v} | {s['accuracy']:.0%} ({round(s['accuracy']*s['n'])}/{s['n']}) | {s['mean_reward']:.2f} | "
                  + " | ".join(s["by_category"].get(c, "-") for c in cats) + " |")
    open("results/summary.md", "w").write("\n".join(md) + "\n")
    print("\n".join(md))
