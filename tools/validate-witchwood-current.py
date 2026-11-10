#!/usr/bin/env python3
"""Validate current compatibility API and every published Witchwood historical interval."""
import copy, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RELEASE="2018-04-13"
DATE=re.compile(r"^\\d{4}-\\d{2}-\\d{2}$")
def read(p): return json.loads(p.read_text(encoding="utf-8"))
catalog=read(ROOT/"cards.json"); render=read(ROOT/"render.json"); legacy=read(ROOT/"history.json")
date_first=read(ROOT/"data/history.json")
research=read(ROOT/"sources/witchwood-research-v1.json")
manifest=read(ROOT/"sources/witchwood-source-manifest.json")
assert date_first["format"]=="date-first-delta"
assert date_first==read(ROOT/"sources/witchwood-history-v2.json")
assert date_first["sourceManifest"]==manifest
base=read(ROOT/"sources/baseline/cards.json")
records={x["id"]:x for x in catalog["cards"]}
rendered={x["id"]:x for x in render["cards"]}
baseline={x["id"]:x for x in base["cards"]}
assert len(records)==len(rendered)==len(baseline)==156
assert len(legacy["cards"])==156
assert manifest["count"]==len(manifest["entries"])==40
assert len(research["observations"])==13
assert len(date_first["observations"])==13
assert len(date_first["events"][RELEASE])==156
assert sum(len(v) for d,v in date_first["events"].items() if d!=RELEASE)==63
assert len(date_first["events"]["2022-11-30"])==25
assert sum(bool(x.get("collectible")) for x in records.values())==135
assert sum(not bool(x.get("collectible")) for x in records.values())==21
ref_count=ref_cards=0
for cid,old in baseline.items():
    now=records[cid]
    for key,value in old.items():
        if key!="nativeTags": assert now.get(key)==value,(cid,key)
    expected=copy.deepcopy(old.get("nativeTags",[]))
    if cid=="GIL_152" and not any(x.get("id")==227 for x in expected):
        expected.append({"id":227,"name":"공격 불가","value":1})
    expected.sort(key=lambda x:x["id"])
    actual=copy.deepcopy(now.get("nativeTags",[])); actual.sort(key=lambda x:x["id"])
    assert actual==expected,(cid,"legacy nativeTags changed")
    refs=now.get("referencedTags",[])
    ref_count+=len(refs); ref_cards+=bool(refs)
    assert rendered[cid]["nativeTags"]==now["nativeTags"],(cid,"render flattened tags")
    assert rendered[cid].get("nativeTagOrigins")==now.get("nativeTagOrigins"),(cid,"render tag roles")
    source=read(ROOT/"data"/(cid+".json"))
    source_base=read(ROOT/"sources/baseline/cards-data"/(cid+".json"))
    assert source["current"]["id"]==cid and source["current"]["dbfId"]==old["dbfId"]
    assert source["mode"]==source_base["mode"] and source["artworkProvenance"]==source_base["artworkProvenance"]
    assert source["card"]["portrait"]==old.get("portrait")
    assert source["card"]["art"]==old.get("art")
    assert source["_meta"]["mode"]==source["mode"]
    assert source["_meta"]["artworkProvenance"]==source["artworkProvenance"]
    assert source["_meta"]["portrait"]==old.get("portrait")
    assert source["_meta"]["art"]==old.get("art")
    assert source["_meta"]["current"]==source["current"]
    assert source["card"]["nativeTags"]==expected
    assert source["current"]["nativeTags"]==expected
    assert source["card"]["nativeTagOrigins"]==now["nativeTagOrigins"]
    assert source["current"]["nativeTagOrigins"]==now["nativeTagOrigins"]
    date_keys=sorted(k for k in source if DATE.fullmatch(k))
    assert date_keys and date_keys[0]==RELEASE,(cid,"missing actual top-level release date key")
    assert date_keys==sorted(x["from"] for x in source["history"]),(cid,"top-level dates/history differ")
    assert source[RELEASE]["type"]==source["initialSpec"]["type"],(cid,"release snapshot mismatch")
    for field,value in source["initialSpec"].items():
        assert source[RELEASE].get(field)==value,(cid,field,"initialSpec not synchronized")
    dbf=str(old["dbfId"])
    assert legacy["cards"][dbf]["id"]==cid
    assert legacy["cards"][dbf]["initialSpec"]==source["initialSpec"]
    assert legacy["cards"][dbf]["patches"]==source["patches"]
    assert rendered[cid]["history"]==source["history"]
    for revision in source["history"]:
        day=revision["from"]
        assert day in source and day in date_first["events"],(cid,day,"missing date-first row")
        snap=source[day]
        for field,value in revision["changes"].items():
            assert snap.get(field)==value,(cid,day,field,"top-level snapshot mismatch")
        restored=copy.deepcopy(rendered[cid])
        restored.update(copy.deepcopy(revision["changes"]))
        for field in revision.get("removedFields",[]): restored.pop(field,None)
        for field,value in revision["changes"].items():
            assert restored.get(field)==value,(cid,day,field,"public current replay mismatch")
        assert restored.get("nativeTags")==snap["nativeTags"],(cid,day,"flattened tag replay")
        assert restored.get("nativeTagOrigins")==snap["nativeTagOrigins"],(cid,day,"tag origin replay")
        assert restored.get("ownedTags")==snap["ownedTags"],(cid,day,"owned tag replay")
        assert restored.get("referencedTags")==snap["referencedTags"],(cid,day,"referenced tag replay")
        assert snap["nativeTags"]==revision["changes"]["nativeTags"],(cid,day,"legacy flat array mismatch")
assert ref_count==25 and ref_cards==20,(ref_count,ref_cards)
# Explicit edge cases that the prior current-only validator missed.
a=read(ROOT/"data/GIL_188a.json"); b=read(ROOT/"data/GIL_188b.json")
assert a[RELEASE]["type"]=="SPELL" and not any(k in a[RELEASE] for k in ("cost","attack","health"))
assert b[RELEASE]["type"]=="SPELL" and not any(k in b[RELEASE] for k in ("cost","attack","health"))
assert a["2018-11-30"]["type"]=="MINION" and a["2018-11-30"]["attack"]==4
assert b["2018-11-30"]["type"]=="MINION" and b["2018-11-30"]["health"]==4
assert read(ROOT/"data/GIL_681.json")[RELEASE]["nativeTags"]
assert next(x for x in read(ROOT/"data/GIL_681.json")[RELEASE]["nativeTags"] if x["id"]==200)["value"]==26
assert read(ROOT/"data/GIL_681.json")["2021-05-13"]["text"]=="<i>모든 종족값을 가집니다.</i>"
assert read(ROOT/"data/GIL_504h.json")[RELEASE]["cost"]==0
assert read(ROOT/"data/GIL_504h.json")[RELEASE]["collectible"] is False
assert read(ROOT/"data/GIL_600.json")[RELEASE]["cost"]==0
assert read(ROOT/"data/GIL_616t2.json")[RELEASE]["text"]==""
assert read(ROOT/"data/GIL_504.json")[RELEASE]["health"]==30
assert read(ROOT/"data/GIL_504.json")[RELEASE]["armor"]==5
for cid,day,tag,value in (("GIL_191","2021-03-26",48,4),("GIL_663","2021-03-26",48,2),("GIL_667","2022-11-30",45,5)):
    tags=read(ROOT/f"data/{cid}.json")[day]["nativeTags"]
    assert next(x for x in tags if x["id"]==tag)["value"]==value
for cid,day in (("GIL_596","2025-03-19"),("GIL_653","2025-03-19"),("GIL_672","2025-03-19")):
    snap=read(ROOT/f"data/{cid}.json")[day]
    assert any(x["id"]==45 for x in snap["nativeTags"])
    assert not any(x["id"]==187 for x in snap["nativeTags"])
for cid in ("GIL_134","GIL_687"):
    assert read(ROOT/f"data/{cid}.json")["2026-03-11"]["nativeRawText"]
for cid in ("GIL_188a","GIL_188b"):
    snap=read(ROOT/f"data/{cid}.json")["2026-07-22"]
    assert any(x["role"]=="owned" for x in snap["nativeTagOrigins"])
for cid in ("GIL_191","GIL_553","GIL_663"):
    assert not any(x["id"]==1452 for x in read(ROOT/f"data/{cid}.json")["2021-03-26"]["nativeTags"])
assert not any(x["id"]==3881 for x in read(ROOT/"data/GIL_553t.json")["2022-11-30"]["nativeTags"])
for cid in ("GIL_191","GIL_663","GIL_600"):
    tags=read(ROOT/f"data/{cid}.json")["2021-03-26"]["nativeTags"]
    assert not any(x["id"]==114 and x.get("value")==0 for x in tags)
break_cards=sum("<br></br>" in x.get("text","") for x in records.values())
assert break_cards==81,break_cards
assert next(x for x in rendered["GIL_152"]["nativeTags"] if x["id"]==227)["value"]==1
print(json.dumps({"cards":156,"baselineCompared":156,"currentNativeTagsPreserved":156,"referencedTags":ref_count,
 "referencedCards":ref_cards,"topLevelDateFiles":156,"existingEvents":40,"newGameplayEvents":13,
 "representationEvents":10,"undeadDateRows":25,"observationGroups":13,"sourceHashes":40,
 "lineBreakCards":break_cards,"legacyReplayIntervals":sum(len(read(ROOT/"data"/(cid+".json"))["history"]) for cid in records),
 "currentTagAddition":"GIL_152:227=1"},ensure_ascii=False))
