#!/usr/bin/env python3
import argparse, json, re, sys
from pathlib import Path

import pandas as pd
import requests

OLLAMA_URL = "http://localhost:11434"  # change if remote
GEN_MODEL = "excel-qa"
EMBED_MODEL = "nomic-embed-text"  # optional if you later add semantic retrieval

SYSTEM_PLANNER = """You convert a user question into a JSON plan of simple table operations
over the provided Excel schema. Only use these operations:

- {"op":"filter_contains","sheet":"<sheet>","column":"<col>","value":"<text>"}
- {"op":"distinct","sheet":"<sheet>","column":"<col>"}
- {"op":"groupby_count","sheet":"<sheet>","by":"<col>","filter": {"column":"<col>","value":"<text>"} optional}
- {"op":"count_rows","sheet":"<sheet>","filter": {"column":"<col>","value":"<text>"} optional}

Rules:
- Use only column names that exist in the schema.
- Prefer case-insensitive substring matches for 'contains' filters.
- Keep the plan SHORT and sufficient.
- If nothing matches the schema, return {"plan": []}.

Respond ONLY with JSON: {"plan": [ ... ]}
"""

PROMPT_PLANNER = """User Question:
{question}

Excel Schema (sheets and columns):
{schema}

Return JSON only.
"""

def ollama_chat(model, messages, stream=False):
    resp = requests.post(f"{OLLAMA_URL}/api/chat", json={"model": model, "messages": messages, "stream": stream})
    resp.raise_for_status()
    data = resp.json()
    return data["message"]["content"]

def to_schema(excel_frames):
    # {"Sheet1": ["Name","Department","..."], ...}
    return {name: list(df.columns.astype(str)) for name, df in excel_frames.items()}

def load_excel(path: Path):
    xls = pd.ExcelFile(path)
    frames = {}
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        # normalize column names for easier matching
        df.columns = [str(c).strip() for c in df.columns]
        # ensure all cells are strings where needed
        frames[sheet] = df
    return frames

def ci_contains(series: pd.Series, value: str):
    return series.astype(str).str.contains(re.escape(value), case=False, na=False)

def execute_plan(plan, frames):
    """Execute plan ops and collect result tables as strings."""
    outputs = []
    for step in plan:
        op = step.get("op")
        sheet = step.get("sheet")
        if sheet not in frames:
            continue
        df = frames[sheet]
        if op == "filter_contains":
            col = step.get("column")
            val = step.get("value","")
            if col in df.columns:
                sub = df[ci_contains(df[col], val)]
                outputs.append((f"{sheet}: filter {col} contains '{val}'", sub))
        elif op == "distinct":
            col = step.get("column")
            if col in df.columns:
                vals = pd.DataFrame({col: sorted(df[col].dropna().astype(str).str.strip().unique())})
                outputs.append((f"{sheet}: distinct {col}", vals))
        elif op == "groupby_count":
            by = step.get("by")
            filt = step.get("filter")
            tmp = df
            if filt and filt.get("column") in df.columns:
                tmp = df[ci_contains(df[filt["column"]], filt.get("value",""))]
            if by in tmp.columns:
                grp = tmp.groupby(by, dropna=False).size().reset_index(name="count").sort_values("count", ascending=False)
                outputs.append((f"{sheet}: count by {by}" + (f" (filtered by {filt['column']} contains '{filt['value']}')" if filt else ""), grp))
        elif op == "count_rows":
            tmp = df
            filt = step.get("filter")
            if filt and filt.get("column") in df.columns:
                tmp = df[ci_contains(df[filt["column"]], filt.get("value",""))]
            outputs.append((f"{sheet}: row_count" + (f" (filtered by {filt['column']} contains '{filt['value']}')" if filt else ""), pd.DataFrame({"row_count":[len(tmp)]})))
        # ignore unknown ops to stay safe
    return outputs

def tabular_context(outputs, max_rows_per=30):
    parts = []
    for title, table in outputs:
        show = table.head(max_rows_per)
        parts.append(f"[{title}]\n{show.to_csv(index=False)}")
    return "\n\n".join(parts) if parts else "(no results)"

def main():
    p = argparse.ArgumentParser(description="Local Excel → LLM QA (Ollama)")
    p.add_argument("--file", required=True, help="Path to .xlsx")
    p.add_argument("--model", default=GEN_MODEL, help="Ollama model name (default: excel-qa)")
    args = p.parse_args()

    excel_path = Path(args.file)
    if not excel_path.exists():
        print(f"File not found: {excel_path}", file=sys.stderr)
        sys.exit(1)

    frames = load_excel(excel_path)
    schema = to_schema(frames)

    print(f"Loaded sheets: {', '.join(frames.keys())}")
    print("Type your question (or 'exit'):")

    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q or q.lower() in {"exit","quit"}:
            break

        # 1) Ask the model to produce a JSON plan based on the schema
        planner_messages = [
            {"role":"system","content": SYSTEM_PLANNER},
            {"role":"user","content": PROMPT_PLANNER.format(question=q, schema=json.dumps(schema, indent=2))}
        ]
        plan_text = ollama_chat("llama3.1", planner_messages, stream=False)  # use base model for planning
        try:
            plan = json.loads(plan_text).get("plan", [])
        except Exception:
            plan = []
        # 2) Execute the plan safely
        outputs = execute_plan(plan, frames)
        context = tabular_context(outputs)

        # 3) Ask the custom model to answer strictly from the context
        messages = [
            {"role":"user", "content": q}
        ]
        payload = {
            "model": args.model,
            "messages": messages,
            # Ollama doesn't have a native "context" field; we inject via template variable .Context by using the 'context' key:
            "context": context
        }
        # The /api/chat endpoint ignores arbitrary keys, so we merge context into the prompt according to our TEMPLATE:
        # We'll emulate TEMPLATE injection here:
        prompt_for_template = q
        final_prompt = f"Question:\n{prompt_for_template}\n\nCONTEXT:\n{context}\n"
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": args.model,
            "prompt": final_prompt,
            "options": {"temperature": 0.2}
        })
        resp.raise_for_status()
        # stream=false behavior: concatenate
        out = ""
        for chunk in resp.iter_lines(decode_unicode=True):
            if not chunk:
                continue
            try:
                j = json.loads(chunk)
                out += j.get("response","")
            except:
                pass
        print(out.strip(), "\n")

if __name__ == "__main__":
    main()
