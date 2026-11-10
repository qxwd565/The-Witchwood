#!/usr/bin/env python3
"""Migrate Witchwood's central date-first archive into card-level v2 and legacy API caches."""
from __future__ import annotations
import copy, json, re, xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RELEASE="2018-04-13"
DATE=re.compile(r"^\d{4}-\d{2}-\d{2}$")
TYPE={3:"HERO",4:"MINION",5:"SPELL",7:"WEAPON",10:"HERO_POWER"}
CLASS={2:"DRUID",3:"HUNTER",4:"MAGE",5:"PALADIN",6:"PRIEST",7:"ROGUE",8:"SHAMAN",9:"WARLOCK",10:"WARRIOR",12:"NEUTRAL"}
RARITY={0:"INVALID",1:"COMMON",2:"FREE",3:"RARE",4:"EPIC",5:"LEGENDARY"}
RACE={2:"DRAENEI",11:"UNDEAD",14:"MURLOC",15:"DEMON",17:"MECHANICAL",18:"ELEMENTAL",20:"BEAST",21:"TOTEM",22:"QUILBOAR",23:"PIRATE",24:"DRAGON",25:"ALL",92:"NAGA"}
RACE_KO={"DRAENEI":"드레나이","UNDEAD":"언데드","MURLOC":"멀록","DEMON":"악마","MECHANICAL":"기계","ELEMENTAL":"정령","BEAST":"야수","TOTEM":"토템","QUILBOAR":"가시멧돼지","PIRATE":"해적","DRAGON":"용족","NAGA":"나가"}
SCHOOL={1:"ARCANE",2:"FIRE",3:"FROST",4:"NATURE",5:"HOLY",6:"SHADOW",7:"FEL"}
TAG_NAMES={32:"발동 효과 표시",45:"생명력",47:"공격력",48:"마나 비용",114:"전설 속성",187:"내구도",190:"도발",194:"천상의 보호막",199:"직업",200:"종족",202:"카드 유형",203:"희귀도",208:"빙결",217:"죽음의 메아리",218:"전투의 함성",219:"비밀",220:"연계",227:"공격 불가",292:"방어도",321:"수집 가능",330:"효과 생성 시각 효과",331:"효과 지속 시각 효과",363:"독성",415:"발견",685:"생명력 흡수",791:"속공",846:"잔상",1342:"발견 시각 효과",1452:"수집품 관련 카드 데이터베이스 ID",1584:"게임 태그 1584",1635:"주문 속성",1965:"게임 태그 1965",2534:"게임 태그 2534",2542:"게임 태그 2542"}

# Only research-confirmed gameplay changes. Wording observations and editor suggestions are excluded.
PATCHES={
"GIL_584":[("2018-07-11",{"races":["DEMON"],"race":"악마"})],
"GIL_545":[("2018-08-03",{"races":[],"race":""})],
"GIL_801":[("2021-03-26",{"cost":1})],
"GIL_191":[("2021-05-13",{"cost":3})],
"GIL_547":[("2022-04-06",{"health":5})],
"GIL_598":[("2022-05-20",{"cost":7})],
"GIL_653":[("2023-04-05",{"text":"<b>죽음의 메아리:</b>"+chr(10)+"무작위 아군 하수인에게 +2/+1을 부여합니다."})],
"GIL_663":[("2023-04-05",{"cost":1,"text":"2/2 나무정령 둘을 내 손으로 가져옵니다."})],
"GIL_663t":[("2023-04-05",{"cost":1})],
"GIL_667":[("2023-05-20",{"health":6,"text":"[x]<b>도발</b>, <b>죽음의 메아리:</b>"+chr(10)+"내 영웅의 생명력을"+chr(10)+"#6 회복시킵니다."})],
"GIL_836":[("2025-03-19",{"text":"[x]<b>전투의 함성</b> 하수인을"+chr(10)+"<b>발견</b>합니다. 그 하수인의"+chr(10)+"비용이 (1) 감소합니다."}),("2026-07-22",{"text":"[x]<b>전투의 함성</b> 하수인을"+chr(10)+"<b>발견</b>합니다."}),("2026-08-19",{"text":"[x]<b>전투의 함성</b> 하수인을"+chr(10)+"<b>발견</b>합니다. 그 하수인의"+chr(10)+"비용이 (1) 감소합니다."})],
"GIL_531":[("2026-04-15",{"cost":0})],
}
UNDEAD={"GIL_117","GIL_198","GIL_207","GIL_510","GIL_513","GIL_515","GIL_526","GIL_545","GIL_553t","GIL_557","GIL_616","GIL_616t","GIL_616t2","GIL_618","GIL_635","GIL_655","GIL_658","GIL_667","GIL_678","GIL_694","GIL_805","GIL_815","GIL_825","GIL_840","GIL_902"}

def read(p): return json.loads(p.read_text(encoding="utf-8"))
def write(p,obj,compact=False):
    p.parent.mkdir(parents=True,exist_ok=True)
    s=json.dumps(obj,ensure_ascii=False,separators=(",",":") if compact else None,indent=None if compact else 2)+"\n"
    if not p.exists() or p.read_text(encoding="utf-8")!=s:
        p.write_text(s,encoding="utf-8",newline="\n"); return True
    return False
def local(tag): return tag.rsplit("}",1)[-1]
def scalar(v):
    if v is None:return None
    if re.fullmatch(r"-?\d+",v):return int(v)
    if re.fullmatch(r"-?\d+\.\d+",v):return float(v)
    return v
def parse_entities(path,wanted):
    out={}
    for _,e in ET.iterparse(path,events=("end",)):
        if local(e.tag)=="Entity":
            cid=e.attrib.get("CardID")
            if cid in wanted:
                owned=[]; refs=[]; strings={}
                for t in list(e):
                    kind=local(t.tag)
                    if kind not in ("Tag","ReferencedTag") or "enumID" not in t.attrib: continue
                    tid=int(t.attrib["enumID"]); value=scalar(t.attrib.get("value"))
                    row={"id":tid}
                    if value is not None: row["value"]=value
                    (owned if kind=="Tag" else refs).append(row)
                    if tid in (184,185):
                        loc={}
                        for child in list(t):
                            name=local(child.tag)
                            if name in ("koKR","enUS"):
                                xmltext=child.text or ""
                                loc[name]={"present":True,"xmlText":xmltext,"nativeRawText":xmltext.replace("\\n","\n")}
                        strings[str(tid)]={"present":True,"locales":loc}
                out[cid]={"ownedTags":owned,"referencedTags":refs,"strings":strings}
            e.clear()
    missing=wanted-set(out)
    if missing: raise ValueError(f"Launch XML missing IDs: {sorted(missing)}")
    return out
def tagmap(rows): return {int(x["id"]):copy.deepcopy(x.get("value")) for x in rows}
def named(rows):
    return [{ "id":x["id"],"name":TAG_NAMES.get(x["id"],f"게임 태그 {x['id']}"),**({"value":x["value"]} if "value" in x else {})} for x in sorted(rows,key=lambda x:x["id"])]
def state_from(entity,cid):
    tags=tagmap(entity["ownedTags"]); kind=TYPE.get(tags.get(202))
    if kind is None: raise ValueError(f"{cid}: unsupported launch type {tags.get(202)}")
    s={"type":kind}
    if tags.get(199) in CLASS:s["cardClass"]=CLASS[tags[199]]
    if tags.get(203) in RARITY:s["rarity"]=RARITY[tags[203]]
    if 321 in tags:s["collectible"]=bool(tags[321])
    if 48 in tags:s["cost"]=tags[48]
    if kind in ("MINION","HERO","HERO_POWER") and 47 in tags:s["attack"]=tags[47]
    if kind=="MINION" and 45 in tags:s["health"]=tags[45]
    if kind=="WEAPON":
        if 47 in tags:s["attack"]=tags[47]
        if 187 in tags:s["durability"]=tags[187]
        elif 45 in tags:s["durability"]=tags[45]
    if kind in ("HERO","HERO_POWER") and 292 in tags:s["armor"]=tags[292]
    if kind=="MINION":
        race=RACE.get(tags.get(200))
        races=[race] if race else []
        for tid,r in ((2540,"ELEMENTAL"),(2542,"BEAST"),(2534,"UNDEAD")):
            if tags.get(tid) not in (None,0,False) and r not in races:races.append(r)
        s["races"]=races
        s["race"]=RACE_KO.get(race,"") if race else ""
    if kind=="SPELL" and tags.get(1635) in SCHOOL:s["spellSchool"]=SCHOOL[tags[1635]]
    for tid,field in ((185,"name"),(184,"nativeRawText")):
        entry=entity["strings"].get(str(tid),{}).get("locales",{}).get("koKR")
        if entry and entry.get("present"):
            s[field]=entry.get("nativeRawText","")
            if tid==184:s["text"]=s[field].replace("[x]","").replace("\n","<br></br>")
    # Canonical applied fields only. HERO native health remains in raw Tag evidence.
    if kind=="SPELL":
        for f in ("attack","health","durability","armor","race","races"):s.pop(f,None)
    if kind=="MINION":
        for f in ("durability","armor","spellSchool"):s.pop(f,None)
    if kind=="WEAPON":
        for f in ("health","armor","race","races","spellSchool"):s.pop(f,None)
    if kind=="HERO":s.pop("health",None)
    if kind=="HERO_POWER":
        for f in ("health","durability","race","races","spellSchool"):s.pop(f,None)
    return s
def api_text(s): return s.replace("\n","<br></br>").replace("\r\n","<br></br>").replace("\r","<br></br>")

def main():
    catalog=read(ROOT/"cards.json"); records={c["id"]:c for c in catalog["cards"]}
    assert len(records)==156
    central=read(ROOT/"data/history.json")
    events=central["events"]
    assert len(events["2018-04-13"])==156
    assert sum(len(v) for d,v in events.items() if d!="2018-04-13")==40
    launch=parse_entities(Path("/tmp/CardDefs-witchwood-launch.xml"),set(records))
    current_entities=parse_entities(Path("/tmp/CardDefs-witchwood-current.xml"),set(records))
    baseline_cards=read(ROOT/"sources/baseline/cards.json") if (ROOT/"sources/baseline/cards.json").exists() else copy.deepcopy(catalog)
    baseline_history=read(ROOT/"sources/baseline/data-history.json") if (ROOT/"sources/baseline/data-history.json").exists() else copy.deepcopy(central)
    # Immutable source guard: baseline copies are captured before first migration and never regenerated.
    if not (ROOT/"sources/baseline/cards.json").exists():
        write(ROOT/"sources/baseline/cards.json",baseline_cards)
        write(ROOT/"sources/baseline/data-history.json",baseline_history)
        for cid in records:
            src=ROOT/"data"/(cid+".json")
            write(ROOT/"sources/baseline/cards-data"/(cid+".json"),read(src))
    original={x["id"]:x for x in baseline_cards["cards"]}
    if set(original)!=set(records): raise ValueError("Baseline/current card ID set drift")
    if len(baseline_history["events"])<4: raise ValueError("Baseline central history missing")
    # Current values are frozen to baseline except the single approved owned Tag 227 addition.
    for cid,card in records.items():
        normalized=copy.deepcopy(card); baseline=copy.deepcopy(original[cid])
        normalized_tags=copy.deepcopy(normalized.pop("nativeTags",[]))+copy.deepcopy(normalized.pop("referencedTags",[]))
        baseline_tags=copy.deepcopy(baseline.pop("nativeTags",[]))+copy.deepcopy(baseline.pop("referencedTags",[]))
        if cid=="GIL_152": baseline_tags.append({"id":227,"name":"공격 불가","value":1})
        normalized_tags.sort(key=lambda x:x["id"]); baseline_tags.sort(key=lambda x:x["id"])
        if normalized_tags!=baseline_tags: raise ValueError(f"{cid}: current owned/referenced tags differ from immutable baseline plus approved GIL_152 Tag227")
        if normalized!=baseline: raise ValueError(f"{cid}: current card metadata changed from immutable baseline")
    # Existing 25 Undead date rows are corrected without changing their actual deltas.
    corrected={}
    for day,group in baseline_history["events"].items():
        newday="2022-11-30" if day=="2022-12-07" else day
        target=corrected.setdefault(newday,{})
        for cid,value in group.items():
            if cid in target and target[cid]!=value: raise ValueError(f"Duplicate conflicting central event {cid} {newday}")
            target[cid]=copy.deepcopy(value)
    if len(corrected["2022-11-30"])!=25: raise ValueError("Undead date correction count mismatch")
    # Apply the only approved current-data addition: CANT_ATTACK=1 on GIL_152.
    current_tags={cid:named(current_entities[cid]["ownedTags"]) for cid in records}
    current_refs={cid:named(current_entities[cid]["referencedTags"]) for cid in records}
    assert any(x.get("id")==227 and x.get("value")==1 for x in current_tags["GIL_152"]), "Current XML must contain CANT_ATTACK=1"
    # Preserve all current non-tag fields byte-for-byte at the JSON-value level.
    for cid,card in records.items():
        src=read(ROOT/"data"/(cid+".json"))
        if src.get("schemaVersion")!=1 or src.get("mode") is None or not isinstance(src.get("artworkProvenance"),dict):
            raise ValueError(f"{cid}: legacy source metadata missing")
        if src["card"].get("portrait")!=original[cid].get("portrait"):raise ValueError(f"{cid}: portrait drift")
        initial=state_from(launch[cid],cid)
        first=corrected.get(RELEASE,{})
        # The old release row is a legacy current snapshot; never use it as launch state.
        old_current=copy.deepcopy(src["card"])
        timeline={RELEASE:{"state":initial,"ownedTags":named(launch[cid]["ownedTags"]),"referencedTags":named(launch[cid]["referencedTags"])}}
        # Confirmed gameplay changes, with full-state deltas built from launch forward.
        for day,changes in PATCHES.get(cid,[]):
            timeline.setdefault(day,{"changes":{},"sources":[]})
            timeline[day]["changes"].update(copy.deepcopy(changes))
        # Existing race/tag events retain their exact dates after the approved correction.
        for day,group in corrected.items():
            if day==RELEASE or cid not in group:continue
            entry=group[cid]
            changes={}
            if "races" in entry:
                changes["races"]=copy.deepcopy(entry["races"])
                changes["race"]=copy.deepcopy(entry.get("race",""))
            if "spellSchool" in entry:changes["spellSchool"]=entry["spellSchool"]
            if changes:
                timeline.setdefault(day,{"changes":{},"sources":[]})
                timeline[day]["changes"].update(changes)
        for day in timeline:
            if day!=RELEASE: timeline[day].setdefault("sources",[])
        # Initial field repairs are asserted against immutable launch parsing.
        # Current values remain the original approved cache.
        dates=sorted(timeline)
        state=copy.deepcopy(initial); states=[]
        for day in dates:
            if day!=RELEASE: state.update(copy.deepcopy(timeline[day].get("changes",{})))
            states.append((day,copy.deepcopy(state)))
        # Preserve the current snapshot exactly; if dated evidence cannot reach it, record it as an undated observation.
        current_state={k:copy.deepcopy(v) for k,v in old_current.items() if k in ("name","type","cardClass","rarity","collectible","cost","text","attack","health","durability","armor","race","races","spellSchool")}
        if "nativeRawText" in src:current_state["nativeRawText"]=copy.deepcopy(src["nativeRawText"])
        latest=states[-1][1]
        undated={}
        for field,value in current_state.items():
            if field in latest and latest[field]!=value:
                undated[field]={"date":None,"before":copy.deepcopy(latest[field]),"after":copy.deepcopy(value),"reason":"current cache differs from dated confirmed events; no date inferred"}
        # Include exact current tags and separate references; do not infer absence as zero.
        owned=named(launch[cid]["ownedTags"]); refs=named(launch[cid]["referencedTags"])
        ref_ids={x["id"] for x in current_refs[cid]}
        tag_states={RELEASE:{"nativeTags":owned,"referencedTags":refs}}
        # The old central snapshots are preserved as explicit dated observations for their recorded cards.
        for day,group in corrected.items():
            if cid not in group:continue
            snap=group[cid]
            if "nativeTags" in snap:
                raw_tags=copy.deepcopy(snap["nativeTags"])
                tag_states[day]={"nativeTags":[x for x in raw_tags if x.get("id") not in ref_ids],\n                                 "referencedTags":[x for x in raw_tags if x.get("id") in ref_ids]}
        # Build fully self-contained historical overrides against the public current card.
        revisions=[]
        for i,(day,hstate) in enumerate(states):
            changes={k:copy.deepcopy(v) for k,v in hstate.items() if k not in ("nativeTags","referencedTags")}
            if "text" in changes: changes["text"]=api_text(changes["text"])
            if day in tag_states:
                changes["nativeTags"]=tag_states[day]["nativeTags"]
                changes["referencedTags"]=tag_states[day]["referencedTags"]
            else:
                changes["nativeTags"]=copy.deepcopy(current_tags[cid])
                changes["referencedTags"]=copy.deepcopy(refs)
            removed=sorted(k for k in current_state if k not in hstate)
            rev={"from":day,"changes":changes}
            if i+1<len(states):rev["before"]=states[i+1][0]
            if removed:rev["removedFields"]=removed
            revisions.append(rev)
        dbf=str(old_current["dbfId"])
        # Public API source retains old metadata and card wrapper; only adds schema-v2 audit material.
        src["schemaVersion"]=2
        src["initialSpec"]=copy.deepcopy(initial)
        src["patches"]=[{"date":rev["from"],"changes":copy.deepcopy(rev["changes"]),"removedFields":copy.deepcopy(rev.get("removedFields",[]))} for rev in revisions[1:]]
        src["current"]=copy.deepcopy(old_current)
        src["current"]["nativeTags"]=copy.deepcopy(current_tags[cid])
        src["current"]["referencedTags"]=copy.deepcopy(current_refs[cid])
        src["history"]=copy.deepcopy(revisions)
        src["observations"]={"undated":undated}
        src["_meta"]={"schemaVersion":2,"timezone":"Asia/Seoul","releasedAt":RELEASE,
                      "source":"HearthSim hsdata immutable launch XML 6317434bee453ec6e8267cbf45277c0a13da90f8",
                      "launchOwnedTags":copy.deepcopy(owned),"launchReferencedTags":copy.deepcopy(refs),
                      "mode":src["mode"],"artworkProvenance":copy.deepcopy(src["artworkProvenance"])}
        write(ROOT/"data"/(cid+".json"),src)
        # cards.json/render.json preserve existing fields; approved Tag addition only.
        records[cid]["nativeTags"]=copy.deepcopy(current_tags[cid])
        records[cid]["referencedTags"]=copy.deepcopy(current_refs[cid])
        # Legacy history uses a full initialSpec and date patches.
        legacy_patches=[]
        for i,rev in enumerate(revisions[1:]):
            legacy_patches.append({"date":rev["from"],"changes":copy.deepcopy(rev["changes"]),"removedFields":copy.deepcopy(rev.get("removedFields",[]))})
    catalog["cards"]=list(records.values())
    # Generate compatibility indexes and a separate explicit date-first canonical source.
    public_history={"schema":2,"timezone":"Asia/Seoul","format":"date-first-delta","cards":{}}
    render=[]
    legacy={"schema":1,"set":"The Witchwood","cards":{}}
    for card in catalog["cards"]:
        cid=card["id"]; src=read(ROOT/"data"/(cid+".json")); dbf=str(card["dbfId"])
        legacy["cards"][dbf]={"id":cid,"initialSpec":src["initialSpec"],"patches":src["patches"]}
        public_history["cards"][cid]={"releasedAt":RELEASE,"initial":src["initialSpec"],"events":src["patches"],"observations":src["observations"]}
        r={k:copy.deepcopy(v) for k,v in card.items()}
        r["history"]=copy.deepcopy(src["history"])
        r["referencedTags"]=copy.deepcopy(src["current"].get("referencedTags",[]))
        render.append(r)
    write(ROOT/"cards.json",catalog,True)
    write(ROOT/"render.json",{"schema":1,"set":"The Witchwood","cards":render},True)
    write(ROOT/"history.json",legacy,True)
    write(ROOT/"sources/witchwood-history-v2.json",public_history)
    print(json.dumps({"cards":len(records),"release":RELEASE,"legacyEvents":40,"correctedUndead":25,
                      "confirmedGameplayPatchEvents":sum(len(v) for v in PATCHES.values()),
                      "currentApprovedTagAddition":"GIL_152:227=1","generated":"cards/render/history + date-first source"},ensure_ascii=False))
if __name__=="__main__":main()
