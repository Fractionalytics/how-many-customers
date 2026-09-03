#!/usr/bin/env python3
"""
Customer base audit + data condition review, as SQL on DuckDB.

    pip install duckdb pandas
    python audit/run.py            # runs every audit/sql/*.sql in order
    python audit/run.py 03         # runs only the files whose name starts with 03

Every SELECT in a .sql file is printed and written to audit/out/<file>__<label>.csv.
Label a SELECT with a comment line immediately above it:  -- @out concentration_top_n
Everything else (CREATE, SET, ...) runs silently. Files share one in-memory database, so
00_model.sql's views are available to every later file. Statements end with a semicolon at
the end of a line.

No conclusions live in this code. The numbers are the numbers; the reasoning is in
audit/FINDINGS.md and the deck.
"""
import os
import re
import sys
import pathlib
import duckdb
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE.parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
os.chdir(DATA)                       # SQL reads the CSVs by bare filename

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 500)
pd.set_option("display.float_format", lambda v: f"{v:,.4f}" if abs(v) < 10 else f"{v:,.1f}")

prefix = sys.argv[1] if len(sys.argv) > 1 else ""
files = sorted(p for p in (HERE / "sql").glob("*.sql") if p.name.startswith(prefix))
if prefix and not any(p.name.startswith("00") for p in files):
    files = [HERE / "sql" / "00_model.sql"] + files      # the model is always needed

con = duckdb.connect()
for f in files:
    sql = f.read_text(encoding="utf-8")
    print("\n" + "=" * 100 + f"\n{f.name}\n" + "=" * 100)
    label = None
    for text in re.split(r";[ \t]*\r?\n", sql):
        m = re.search(r"--\s*@out\s+(\S+)", text)
        if m:
            label = m.group(1)
        body = re.sub(r"--[^\n]*", "", text).strip()
        if not body:
            continue
        is_select = re.match(r"(?is)^\s*(select|with|from|pivot|unpivot)\b", body) is not None
        if is_select:
            df = con.execute(body).df()
            name = label or f"q{len(list(OUT.glob(f.stem + '__*'))) + 1}"
            print(f"\n-- {name}")
            print(df.to_string(index=False))
            df.to_csv(OUT / f"{f.stem}__{name}.csv", index=False)
            label = None
        else:
            con.execute(body)
con.close()
