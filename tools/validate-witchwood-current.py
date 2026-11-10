#!/usr/bin/env python3
"""Final independent validator for Witchwood sparse source, raw replay, and public compatibility."""
import base64,gzip,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATE=re.compile(r"^\d{4}-\d{2}-\d{2}$")
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
date_rows=sum(sum(1 for k in x if DATE.fullmatch(k) and k!="2018-04-13") for x in files.values())
assert date_rows==63,date_rows
gameplay_rows=sum(1 for src in files.values() for day,row in src.items() if DATE.fullmatch(day) and day!="2018-04-13" and set(row.get("eventKinds",[])) & {"gameplay","existing-confirmed"})
representation_rows=sum(1 for src in files.values() for day,row in src.items() if DATE.fullmatch(day) and day!="2018-04-13" and "representation" in row.get("eventKinds",[]))
assert (gameplay_rows,representation_rows)==(53,10),(gameplay_rows,representation_rows)
undated_r005=sum(1 for group in central["observations"] for item in group.get("extraUndatedEvidence",[]) if item.get("findingId")=="WITCH-BAL-R005")
assert undated_r005==2
assert intervals==156+gameplay_rows+representation_rows
for d in audit["rawReplayDiffs"]:
 rev=next(x for x in files[d["id"]]["history"] if x["from"]==d["day"])
 tag=next((x for x in rev["changes"][d["role"]] if int(x["id"])==int(d["tag"])),None)
 actual="ABSENT" if tag is None else str(tag.get("value")) if "value" in tag else "NO_VALUE"
 assert actual==d["expected"],(d["id"],d["day"],d["tag"],actual,d["expected"])
for d in audit["initialLogicalDiffs"]:
 assert files[d["id"]]["initialSpec"].get(d["field"],"ABSENT")==d["expected"],(d["id"],d["field"])
for cid,tid in (("GIL_188a",791),("GIL_188b",190)):
 assert "2026-07-22" in files[cid]
 row=files[cid]["2026-07-22"]
 assert row["eventKinds"]==["representation"]
 assert row["rawTagDelta"][0]["operation"]=="roleTransfer" and row["rawTagDelta"][0]["id"]==tid
 assert any(x.get("findingId")=="WITCH-BAL-R005" for group in files[cid]["observations"]["research"] for x in group.get("extraUndatedEvidence",[]))
assert not any(x["id"]==2 for x in files["GIL_547"]["2022-04-06"]["rawTagDelta"])
assert not any(x["id"]==2831 for x in files["GIL_663t"]["2023-04-05"]["rawTagDelta"])
for cid,tid in (("GIL_547",2),("GIL_663t",2831),("GIL_663",1452)):
 assert any(x["tagId"]==tid and x["date"] is None for x in files[cid]["observations"]["undatedRawTags"]),(cid,tid)
print(json.dumps({"cards":156,"sparseDateRows":date_rows,"datedIntervals":intervals,"gameplay":gameplay_rows,"representation":representation_rows,"undatedR005":undated_r005,"rawDiffs":51,"logicalDiffs":22,"collectible":135,"nonCollectible":21},ensure_ascii=False))
