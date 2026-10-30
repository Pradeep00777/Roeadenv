"""Non-LLM baselines. They exist to calibrate the environment, not to be good.

refuse_all      always says not_available (floor: shows what refusing earns).
table_reader    the typical 'retrieve + regex' pipeline: BM25 search, find the row that names the
                entity, map the question's year to a column using the nearest header line of years,
                take that cell. Falls back to the best-matching sentence's number for prose questions.
table_reader_oracle   same extractor but handed the correct page: separates retrieval misses from
                extraction misses.
"""
import re

PLACES = ["Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana",
          "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
          "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
          "Tripura", "Uttarakhand", "Uttar Pradesh", "West Bengal", "Andaman & Nicobar", "Chandigarh",
          "Dadra & Nagar Haveli", "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry", "Jaipur"]
YEAR = re.compile(r"\b(20[12]\d)\b")
CELL = re.compile(r"NA|-?\d[\d,]*\.?\d*")

def refuse_all(env, task):
    env.reset(task)
    return env.submit(None, "not_available", None)

def _entity(q):
    # longest match first so 'Uttar Pradesh' beats 'Pradesh' and 'Uttarakhand' is distinct
    hits = [p for p in sorted(PLACES, key=len, reverse=True) if p.lower() in q.lower()]
    return hits[0] if hits else None

def _header_years(lines, upto):
    for i in range(upto, -1, -1):
        ys = YEAR.findall(lines[i])
        if len(ys) >= 3:
            return ys
    return None

def _extract(page_text, q):
    """Return (value, status) from one page, or (None, None) if nothing usable."""
    lines = page_text.splitlines()
    ent, years = _entity(q), YEAR.findall(q)
    year = years[-1] if years else None
    if ent:
        key = ent.split()[0].lower() if ent.startswith(("Andaman", "Dadra")) else ent.lower()
        for i, ln in enumerate(lines):
            if ln.lower().strip().split("  ")[0].strip().lstrip("0123456789 ").startswith(key) or \
               re.match(r"\s*\d*\s*" + re.escape(key), ln.lower()):
                after = ln[ln.lower().index(key) + len(key):]   # keep case so 'NA' survives
                cells = CELL.findall(after)
                if not cells:
                    continue
                hy = _header_years(lines, i)
                idx = hy.index(year) if (hy and year in hy) else 0
                if idx >= len(cells):
                    continue
                v = cells[idx]
                return (None, "not_available") if v == "NA" else (v, "answered")
        return None, None
    # no named place: national row that starts with the year (e.g. Table 1.1), else best prose line
    if year:
        for ln in lines:
            m = re.match(r"\s*" + year + r"\s+([\d,]{5,})", ln)
            if m:
                return m.group(1), "answered"
    qt = set(re.findall(r"[a-z]{4,}", q.lower()))
    best, score = None, 0
    for ln in lines:
        nums = [c for c in CELL.findall(ln) if c != "NA" and not YEAR.fullmatch(c.rstrip(",."))]
        s = len(qt & set(re.findall(r"[a-z]{4,}", ln.lower())))
        if nums and s > score:
            best, score = nums[0], s
    return (best, "answered") if best else (None, None)

def _which(q):
    return q.lower().startswith("which")

def table_reader(env, task, oracle=False, k=3):
    obs = env.reset(task)
    q = obs["question"]
    pages = task["pages"][:1] if (oracle and task["pages"]) else [h["page"] for h in env.search(q, k)]
    for p in pages:
        txt = env.read_page(p)
        if _which(q):
            # pick the first place named on the best page: a crude 'top row' reading
            for ln in txt.splitlines():
                e = _entity(ln)
                if e:
                    return env.submit(e, "answered", p)
            continue
        v, st = _extract(txt, q)
        if st == "not_available":
            return env.submit(None, "not_available", p)
        if v is not None:
            return env.submit(v, "answered", p)
    return env.submit(None, "not_available", None)

def table_reader_oracle(env, task):
    return table_reader(env, task, oracle=True)

AGENTS = {"refuse_all": refuse_all, "table_reader": table_reader, "table_reader_oracle": table_reader_oracle}
