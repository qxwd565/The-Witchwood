#!/usr/bin/env python3
"""Final independent source validator; detailed raw and replay assertions live in test_witchwood_v2.py."""
import base64,gzip,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p): return json.loads(p.read_text(encoding="utf-8"))
def ev(p): return json.loads(gzip.decompress(base64.b64decode((ROOT/p).read_text(encoding="utf-8").splitlines()[-1].strip())))
catalog=read(ROOT/"cards.json"); render=read(ROOT/"render.json"); legacy=read(ROOT/"history.json")["cards"]
central=read(ROOT/"data/history.json"); audit=ev("sources/witchwood-independent-audit-v2.json.gz.b64")
files={p.stem:read(p) for p in (ROOT/"data").glob("GIL_*.json")}
assert len(catalog["cards"])==len(render["cards"])==len(files)==156
assert len(legacy)==156 and len(central["events"]["2018-04-13"])==156
assert central["schema"]==3 and central["format"]=="date-first-delta-v3"
assert len(audit["rawReplayDiffs"])==51 and len(audit["initialLogicalDiffs"])==22
assert len(audit["existingRawDelta40"])==40 and len(audit["extraUndatedEvidence"]["observations"])==9
assert sum(bool(x.get("collectible")) for x in catalog["cards"])==135
assert sum(not bool(x.get("collectible")) for x in catalog["cards"])==21
intervals=sum(len(x["history"]) for x in files.values())
assert intervals==219,intervals
date_rows=sum(sum(1 for k in x if re.fullmatch(r"\d{4}-\d{2}-\d{2}",k) and k!="2018-04-13") for x in files.values())
assert date_rows==63,date_rows
for d in audit["rawReplayDiffs"]:
 rev=next(x for x in files[d["id"]]["history"] if x["from"]==d["day"])
 tag=next((x for x in rev["changes"][d["role"]] if int(x["id"])==int(d["tag"])),None)
 actual="ABSENT" if tag is None else str(tag.get("value")) if "value" in tag else "NO_VALUE"
 assert actual==d["expected"],(d["id"],d["day"],d["tag"],actual,d["expected"])
for d in audit["initialLogicalDiffs"]:
 assert files[d["id"]]["initialSpec"].get(d["field"],"ABSENT")==d["expected"],(d["id"],d["field"])
print(json.dumps({"cards":156,"sparseDateRows":date_rows,"legacyIntervals":intervals,"rawDiffs":51,"logicalDiffs":22,"collectible":135,"nonCollectible":21},ensure_ascii=False))
