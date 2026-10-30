"""Deterministic grader. No model in the loop: the same submission always gets the same score.

reward = correct * (0.8 + 0.2 * citation_ok)
outcome labels (used for the failure taxonomy):
  correct | wrong_value | false_refusal (refused an answerable question) |
  hallucinated (answered an unanswerable one) | unparseable
"""
import re

LAKH = re.compile(r"([\d\.]+)\s*lakh", re.I)
CRORE = re.compile(r"([\d\.]+)\s*crore", re.I)
NUM = re.compile(r"-?\d[\d,]*\.?\d*")

def parse_number(x):
    """Accepts 487707, '4,87,707', '4.88 lakh', '-1.38%', ' 70.28 '. Returns float or None."""
    if x is None or isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x)
    m = LAKH.search(s)
    if m:
        return float(m.group(1)) * 1e5
    m = CRORE.search(s)
    if m:
        return float(m.group(1)) * 1e7
    m = NUM.search(s)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None

def _norm(s):
    return re.sub(r"[^a-z]", "", str(s).lower())

def citation_ok(task, page, pages):
    if task["type"] == "na":
        return True  # nothing to cite when the answer is "not available"
    if page is None:
        return False
    try:
        page = int(page)
    except (TypeError, ValueError):
        return False
    if page in task.get("extra_pages", []):
        return True
    ev = task.get("evidence")
    if not ev:
        return page in task["pages"]
    return any(re.search(ev, line) for line in pages.get(page, "").splitlines())

def grade(task, sub, pages):
    status = (sub.get("status") or "answered").strip().lower()
    ans = sub.get("answer")
    exp = task["answer"]
    if task["type"] == "na":
        correct = status == "not_available"
        outcome = "correct" if correct else "hallucinated"
    elif status == "not_available":
        correct, outcome = False, "false_refusal"
    elif task["type"] == "str":
        ok = {_norm(exp)} | {_norm(a) for a in task.get("aliases", [])}
        correct = _norm(ans) in ok
        outcome = "correct" if correct else "wrong_value"
    else:
        v = parse_number(ans)
        if v is None:
            correct, outcome = False, "unparseable"
        else:
            if task["type"] == "int":
                correct = abs(v - exp) < 1e-9
            else:
                correct = abs(v - exp) <= (task.get("tol") or 0) + 1e-9
            outcome = "correct" if correct else "wrong_value"
    cite = citation_ok(task, sub.get("citation_page"), pages) if correct else False
    return {"id": task["id"], "category": task["category"], "correct": bool(correct), "citation_ok": bool(cite),
            "reward": round((1.0 if correct else 0.0) * (0.8 + 0.2 * cite), 3), "outcome": outcome,
            "submitted": {"answer": ans, "status": status, "citation_page": sub.get("citation_page")},
            "expected": exp}
