"""RoadEnv: a small tool-use evaluation environment over a real, messy government report.

An agent gets one question per episode and a budget of tool calls:
  search(query, k)      -> BM25 hits: [{page, score, snippet}]
  read_page(page)       -> full text of one PDF page (layout-preserved)
  calculate(expression) -> arithmetic only (+ - * / ** parentheses, round, abs)
  submit(answer, status, citation_page)  -> ends the episode, returns the graded result

Corpus variants:
  "text"      the PDF's own text layer (pdftotext -layout). 130 of 266 pages are empty here,
              including every Annexure table.
  "text+ocr"  same, plus tesseract OCR (--psm 1, auto-rotation) for those empty pages.
"""
import json, math, os, re
from rank_bm25 import BM25Okapi
from .grader import grade

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = re.compile(r"[a-z]+|\d[\d,\.]*")

STOP = set("""a an the of in on at to for by and or is was were be been what which who how many much did does do
report reported reporting according per as from with its it this that than over under into number total""".split())

def _tok(s):
    return [w.replace(",", "") for w in TOKEN.findall(s.lower()) if w not in STOP]

def load_pages(variant="text"):
    pages = {}
    for line in open(os.path.join(HERE, "data", "pages_text.jsonl")):
        r = json.loads(line); pages[r["page"]] = r["text"]
    if variant == "text+ocr":
        for line in open(os.path.join(HERE, "data", "pages_ocr.jsonl")):
            r = json.loads(line)
            if not pages[r["page"]].strip():
                pages[r["page"]] = r["text"]
    return pages

def load_tasks():
    return [json.loads(l) for l in open(os.path.join(HERE, "tasks.jsonl"))]

_SAFE = re.compile(r"^[\d\s\.\+\-\*/\(\),a-z_]*$")
def _calc(expr):
    e = expr.replace(",", "").lower()
    if not _SAFE.match(e):
        raise ValueError("only arithmetic is allowed")
    return eval(e, {"__builtins__": {}}, {"round": round, "abs": abs, "min": min, "max": max})

class RoadEnv:
    def __init__(self, variant="text", max_steps=10):
        self.variant, self.max_steps = variant, max_steps
        self.pages = load_pages(variant)
        self.ids = sorted(self.pages)
        self.bm25 = BM25Okapi([_tok(self.pages[i]) or ["_empty_"] for i in self.ids])
        # citation checks always look at text + OCR, so they do not depend on the agent's corpus
        self.cite_pages = load_pages("text+ocr")

    # ---- episode control
    def reset(self, task):
        self.task, self.steps, self.done, self.trace = task, 0, False, []
        return {"question": task["question"], "tools": ["search", "read_page", "calculate", "submit"],
                "max_steps": self.max_steps,
                "answer_format": {"answer": "number or string, null if not available",
                                  "status": "answered | not_available", "citation_page": "PDF page number"}}

    def _tick(self, name, args, out):
        self.steps += 1
        self.trace.append({"tool": name, "args": args, "out": out if name != "read_page" else f"<{len(out)} chars>"})
        if self.steps > self.max_steps and not self.done:
            raise RuntimeError("step budget exhausted")

    # ---- tools
    def search(self, query, k=5):
        sc = self.bm25.get_scores(_tok(query))
        top = sorted(zip(self.ids, sc), key=lambda x: -x[1])[:k]
        hits = [{"page": p, "score": round(float(s), 3),
                 "snippet": re.sub(r"\s+", " ", self.pages[p]).strip()[:200]} for p, s in top]
        self._tick("search", {"query": query, "k": k}, [h["page"] for h in hits])
        return hits

    def read_page(self, page):
        out = self.pages.get(int(page), "")
        self._tick("read_page", {"page": page}, out)
        return out

    def calculate(self, expression):
        try:
            out = _calc(expression)
        except Exception as e:
            out = f"error: {e}"
        self._tick("calculate", {"expression": expression}, out)
        return out

    def submit(self, answer, status="answered", citation_page=None):
        self.done = True
        res = grade(self.task, {"answer": answer, "status": status, "citation_page": citation_page}, self.cite_pages)
        res["steps"] = self.steps + 1
        res["trace"] = self.trace
        return res
