"""Plug-in LLM agent (ReAct-style JSON tool calls) for any OpenAI-compatible chat endpoint.

NOT RUN in the published results: no model API key was available where this was built.
To run:
  export LLM_BASE_URL=https://api.groq.com/openai/v1   # or any OpenAI-compatible URL
  export LLM_API_KEY=...            LLM_MODEL=llama-3.3-70b-versatile
  python run_eval.py --agent llm --variant text
"""
import json, os, re, urllib.request

SYSTEM = """You answer questions about the report 'Road Accidents in India 2024' (MoRTH) using tools.
Reply with exactly one JSON object per turn, nothing else:
  {"tool": "search", "query": "...", "k": 5}
  {"tool": "read_page", "page": 105}
  {"tool": "calculate", "expression": "(286-290)/290*100"}
  {"tool": "submit", "answer": <number|string|null>, "status": "answered"|"not_available", "citation_page": <int|null>}
Rules: numbers in the report use Indian grouping (4,87,707 = 487707). Cite the PDF page you read the value on.
If the report does not contain the answer, submit status "not_available". Compute derived values with calculate."""

def _chat(messages):
    req = urllib.request.Request(
        os.environ["LLM_BASE_URL"].rstrip("/") + "/chat/completions",
        data=json.dumps({"model": os.environ["LLM_MODEL"], "messages": messages, "temperature": 0}).encode(),
        headers={"Authorization": "Bearer " + os.environ["LLM_API_KEY"], "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["choices"][0]["message"]["content"]

def llm_agent(env, task):
    obs = env.reset(task)
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps(obs)}]
    for _ in range(obs["max_steps"]):
        raw = _chat(msgs)
        msgs.append({"role": "assistant", "content": raw})
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            act = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            act = {}
        tool = act.get("tool")
        if tool == "submit":
            return env.submit(act.get("answer"), act.get("status", "answered"), act.get("citation_page"))
        if tool == "search":
            out = env.search(act.get("query", ""), int(act.get("k", 5)))
        elif tool == "read_page":
            out = env.read_page(act.get("page", 0))[:6000]
        elif tool == "calculate":
            out = env.calculate(act.get("expression", ""))
        else:
            out = "error: reply with one JSON tool call"
        msgs.append({"role": "user", "content": json.dumps({"observation": out})})
    return env.submit(None, "not_available", None)
