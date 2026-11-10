#!/usr/bin/env python3
"""Compare every preserved immutable baseline file with the original repository commit."""
import json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE="0a849efcc23669bcb3929246d9de62e7ce85837b"
def local(path): return json.loads((ROOT/path).read_text(encoding="utf-8"))
def original(path):
    result=subprocess.run(["git","show",f"{BASE}:{path}"],cwd=ROOT,capture_output=True,text=True,check=True)
    return json.loads(result.stdout)
assert local("sources/baseline/cards.json")==original("cards.json"),"cards.json baseline differs from 0a849ef"
assert local("sources/baseline/data-history.json")==original("data/history.json"),"data/history.json baseline differs from 0a849ef"
ids={x["id"] for x in original("cards.json")["cards"]}
files={p.stem for p in (ROOT/"sources/baseline/cards-data").glob("GIL_*.json")}
assert len(ids)==156 and files==ids,(len(ids),len(files),sorted(ids-files),sorted(files-ids))
for cid in sorted(ids):
    assert local(f"sources/baseline/cards-data/{cid}.json")==original(f"data/{cid}.json"),cid
print(json.dumps({"baselineCommit":BASE,"cards":len(ids),"cardDataFiles":len(files),"cardsJson":"identical","centralHistory":"identical"},ensure_ascii=False))
