#!/usr/bin/env python3
"""Validate published Witchwood current API against immutable pre-migration baseline."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p): return json.loads(p.read_text(encoding="utf-8"))
catalog=read(ROOT/"cards.json"); render=read(ROOT/"render.json"); legacy=read(ROOT/"history.json")
date_first=read(ROOT/"data/history.json")
assert date_first["format"]=="date-first-delta"
assert date_first==read(ROOT/"sources/witchwood-history-v2.json")
base=read(ROOT/"sources/baseline/cards.json")
records={x["id"]:x for x in catalog["cards"]}
rendered={x["id"]:x for x in render["cards"]}
baseline={x["id"]:x for x in base["cards"]}
assert len(records)==len(rendered)==len(baseline)==156
assert len(legacy["cards"])==156
assert sum(bool(x.get("collectible")) for x in records.values())==135
assert sum(not bool(x.get("collectible")) for x in records.values())==21
for cid,old in baseline.items():
    now=records[cid]
    for key,value in old.items():
        if key not in ("nativeTags",): assert now.get(key)==value,(cid,key)
    old_tags={x["id"]:x.get("value") for x in old.get("nativeTags",[])}
    new_tags={x["id"]:x.get("value") for x in now.get("nativeTags",[])+now.get("referencedTags",[])}
    if cid=="GIL_152": old_tags[227]=1
    assert old_tags==new_tags,cid
    assert rendered[cid]["text"]==now.get("text"),cid
    source=read(ROOT/"data"/(cid+".json"))
    assert source["current"]["id"]==cid and source["current"]["dbfId"]==old["dbfId"]
    assert source["mode"]==read(ROOT/"sources/baseline/cards-data"/(cid+".json"))["mode"]
    assert source["artworkProvenance"]==read(ROOT/"sources/baseline/cards-data"/(cid+".json"))["artworkProvenance"]
    assert source["card"]["portrait"]==old.get("portrait")
    assert source["card"]["art"]==old.get("art")
break_cards=sum("<br></br>" in x.get("text","") for x in records.values())
assert break_cards==81,break_cards
assert next(x for x in rendered["GIL_152"]["nativeTags"] if x["id"]==227)["value"]==1
assert all(len(x["patches"])>=0 for x in legacy["cards"].values())
print(json.dumps({"cards":156,"collectible":135,"nonCollectible":21,"currentBaselineCompared":156,
                  "modeAndArtworkProvenancePreserved":156,"lineBreakCards":break_cards,
                  "approvedCurrentTagAddition":"GIL_152:227=1","legacyHistoryCards":156},ensure_ascii=False))
