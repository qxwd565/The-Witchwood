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
for cid,want in {
 "GIL_188a":{"45":"2","47":"4","48":"3","183":"1125","199":"2","200":"20","202":"4","203":"1"},
 "GIL_188b":{"45":"4","47":"2","48":"3","183":"1125","199":"2","202":"4","203":"1"}
}.items():
 release=files[cid]["initialSpec"]
 release_tags={str(x["id"]):str(x["value"]) for x in release["ownedTags"] if "value" in x}
 assert release_tags.get("202")=="5" and "rarity" not in release,(cid,"launch SPELL baseline")
 row=files[cid]["2018-11-30"]
 assert row["type"]=="MINION" and row["rarity"]=="COMMON",(cid,"R001 logical preview")
 state=next(x["changes"] for x in files[cid]["history"] if x["from"]=="2018-11-30")
 actual={str(x["id"]):str(x["value"]) for x in state["ownedTags"] if "value" in x}
 assert actual==want,(cid,"R001 exact scalar raw state",actual)
 assert state["referencedTags"]==[],(cid,"R001 references")
 assert all(any(int(x["id"])==tid for x in state["ownedTags"]) for tid in (184,185,342)),(cid,"preserved strings")
 assert not any(int(x["id"]) in (190,791) for x in state["ownedTags"]),(cid,"no future keyword at R001")
 later=next(x["changes"] for x in files[cid]["history"] if x["from"]=="2026-07-22")
 later_tags={str(x["id"]):str(x["value"]) for x in later["ownedTags"] if "value" in x}
 assert later["rarity"]=="COMMON" and later_tags.get("202")=="4",(cid,"R005 cumulative type/rarity")
 assert later_tags.get("45")==want["45"] and later_tags.get("47")==want["47"] and later_tags.get("48")=="3" and later_tags.get("203")=="1",(cid,"R005 cumulative scalars")
 assert later_tags.get("791" if cid=="GIL_188a" else "190")=="1",(cid,"R005 owned keyword")
 generated={int(x["tagId"]) for x in files[cid]["observations"]["undatedRawTags"] if x.get("findingId") is None}
 final=files[cid]["history"][-1]["changes"]
 def scalar(rows): return {int(x["id"]):str(x["value"]) for x in rows if "value" in x}
 actual_diff=set()
 for role in ("ownedTags","referencedTags"):
  before={int(x["id"]):x for x in final.get(role,[])}
  after={int(x["id"]):x for x in files[cid]["current"].get(role,[])}
  actual_diff.update(tid for tid in set(before)|set(after) if before.get(tid,"ABSENT")!=after.get(tid,"ABSENT"))
 explicit={int(x["tagId"]) for x in files[cid]["observations"]["undatedRawTags"] if x.get("findingId") is not None}
 assert generated==actual_diff-explicit,(cid,"undated raw observations recomputed",generated,actual_diff,explicit)
expected_preview={
 "GIL_188a":{"nativeRawText":"<b>속공</b>","text":"<b>속공</b>","cost":3,"attack":4,"health":2,"races":["BEAST"],"race":"야수"},
 "GIL_188b":{"nativeRawText":"<b>도발</b>","text":"<b>도발</b>","cost":3,"attack":2,"health":4,"races":[],"race":""}}
render_by_id={x["id"]:x for x in render["cards"]}
for cid,fields in expected_preview.items():
 src=files[cid]
 for day in ("2018-11-30","2026-07-22"):
  sparse=src[day]
  if day=="2018-11-30":
   for field,want in fields.items(): assert sparse.get(field,"__MISSING__")==want,(cid,day,field,"sparse")
   assert sparse["type"]=="MINION" and sparse["rarity"]=="COMMON",(cid,day,"logical type/rarity")
  revision=next(x for x in src["history"] if x["from"]==day)
  for field,want in fields.items(): assert revision["changes"].get(field,"__MISSING__")==want,(cid,day,field,"history")
  assert revision["changes"]["type"]=="MINION" and revision["changes"]["rarity"]=="COMMON"
  restored=dict(render_by_id[cid]); restored.update(revision["changes"])
  for field in revision.get("removedFields",[]): restored.pop(field,None)
  for field,want in fields.items(): assert restored.get(field,"__MISSING__")==want,(cid,day,field,"legacy current+changes/removedFields")
  assert restored.get("type")=="MINION" and restored.get("rarity")=="COMMON",(cid,day,"legacy logical")
 assert "rarity" not in src.get("observations",{}).get("undated",{})
 for field in fields: assert field not in src.get("observations",{}).get("undated",{}),(cid,field,"false undated logical observation")
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
