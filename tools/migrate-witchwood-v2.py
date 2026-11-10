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
RACE={2:"DRAENEI",11:"UNDEAD",14:"MURLOC",15:"DEMON",17:"MECHANICAL",18:"ELEMENTAL",20:"BEAST",21:"TOTEM",22:"QUILBOAR",23:"PIRATE",24:"DRAGON",26:"ALL",92:"NAGA"}
RACE_KO={"DRAENEI":"드레나이","UNDEAD":"언데드","MURLOC":"멀록","DEMON":"악마","MECHANICAL":"기계","ELEMENTAL":"정령","BEAST":"야수","TOTEM":"토템","QUILBOAR":"가시멧돼지","PIRATE":"해적","DRAGON":"용족","ALL":"모든 종족","NAGA":"나가"}
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
"GIL_653":[("2023-04-05",{"nativeRawText":"<b>죽음의 메아리:</b>"+chr(10)+"무작위 아군 하수인에게 +2/+1을 부여합니다.","text":"<b>죽음의 메아리:</b><br></br>무작위 아군 하수인에게 +2/+1을 부여합니다."})],
"GIL_663":[("2023-04-05",{"cost":1,"nativeRawText":"2/2 나무정령 둘을 내 손으로 가져옵니다.","text":"2/2 나무정령 둘을 내 손으로 가져옵니다."})],
"GIL_663t":[("2023-04-05",{"cost":1})],
"GIL_667":[("2023-05-20",{"health":6,"nativeRawText":"[x]<b>도발</b>, <b>죽음의 메아리:</b>"+chr(10)+"내 영웅의 생명력을"+chr(10)+"#6 회복시킵니다.","text":"<b>도발</b>, <b>죽음의 메아리:</b><br></br>내 영웅의 생명력을<br></br>#6 회복시킵니다."})],
"GIL_836":[("2025-03-19",{"nativeRawText":"[x]<b>전투의 함성</b> 하수인을"+chr(10)+"<b>발견</b>합니다. 그 하수인의"+chr(10)+"비용이 (1) 감소합니다.","text":"<b>전투의 함성</b> 하수인을<br></br><b>발견</b>합니다. 그 하수인의<br></br>비용이 (1) 감소합니다."}),("2026-07-22",{"nativeRawText":"[x]<b>전투의 함성</b> 하수인을"+chr(10)+"<b>발견</b>합니다.","text":"<b>전투의 함성</b> 하수인을<br></br><b>발견</b>합니다."}),("2026-08-19",{"nativeRawText":"[x]<b>전투의 함성</b> 하수인을"+chr(10)+"<b>발견</b>합니다. 그 하수인의"+chr(10)+"비용이 (1) 감소합니다.","text":"<b>전투의 함성</b> 하수인을<br></br><b>발견</b>합니다. 그 하수인의<br></br>비용이 (1) 감소합니다."})],
"GIL_531":[("2026-04-15",{"cost":0})],
}
REPRESENTATION_PATCHES={
 "GIL_188a":[("2018-11-30",{"type":"MINION","cost":3,"attack":4,"health":2,"races":["BEAST"],"race":"야수","nativeRawText":"<b>속공</b>","text":"<b>속공</b>","nativeTags":[{"id":45,"name":"생명력","value":2},{"id":47,"name":"공격력","value":4},{"id":48,"name":"마나 비용","value":3},{"id":183,"name":"게임 태그 183","value":1125},{"id":199,"name":"직업","value":2},{"id":200,"name":"종족","value":20},{"id":202,"name":"카드 유형","value":4},{"id":203,"name":"희귀도","value":1}],"nativeTagOrigins":[{"id":45,"role":"owned"},{"id":47,"role":"owned"},{"id":48,"role":"owned"},{"id":183,"role":"owned"},{"id":199,"role":"owned"},{"id":200,"role":"owned"},{"id":202,"role":"owned"},{"id":203,"role":"owned"}]}),("2026-07-22",{"nativeTagRoleChange":{"791":"owned"}})],
 "GIL_188b":[("2018-11-30",{"type":"MINION","cost":3,"attack":2,"health":4,"races":[],"race":"","nativeRawText":"<b>도발</b>","text":"<b>도발</b>","nativeTags":[{"id":45,"name":"생명력","value":4},{"id":47,"name":"공격력","value":2},{"id":48,"name":"마나 비용","value":3},{"id":183,"name":"게임 태그 183","value":1125},{"id":190,"name":"도발","value":1},{"id":199,"name":"직업","value":2},{"id":202,"name":"카드 유형","value":4},{"id":203,"name":"희귀도","value":1}],"nativeTagOrigins":[{"id":45,"role":"owned"},{"id":47,"role":"owned"},{"id":48,"role":"owned"},{"id":183,"role":"owned"},{"id":190,"role":"owned"},{"id":199,"role":"owned"},{"id":202,"role":"owned"},{"id":203,"role":"owned"}]}),("2026-07-22",{"nativeTagRoleChange":{"190":"owned"}})],
 "GIL_681":[("2021-05-13",{"nativeRawText":"<i>모든 종족값을 가집니다.</i>","text":"<i>모든 종족값을 가집니다.</i>","races":["ALL"],"race":"모든 종족"})],
 "GIL_596":[("2025-03-19",{"tagStorage":"DURABILITY_187_TO_HEALTH_45"})],
 "GIL_653":[("2025-03-19",{"tagStorage":"DURABILITY_187_TO_HEALTH_45"})],
 "GIL_672":[("2025-03-19",{"tagStorage":"DURABILITY_187_TO_HEALTH_45"})],
 "GIL_134":[("2026-03-11",{"nativeRawText":"하수인에게 피해를 $4 줍니다. 그 하수인이 죽으면 그 카드를 복사하여 내 손으로 가져옵니다.","text":"하수인에게 피해를 $4 줍니다. 그 하수인이 죽으면 그 카드를 복사하여 내 손으로 가져옵니다."})],
 "GIL_687":[("2026-03-11",{"nativeRawText":"하수인에게 피해를 $3 줍니다."+chr(10)+"그 하수인이 죽으면 동전을"+chr(10)+"내 손으로 가져옵니다.","text":"하수인에게 피해를 $3 줍니다.<br></br>그 하수인이 죽으면 동전을<br></br>내 손으로 가져옵니다."})],
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
                if cid not in out:
                    out[cid]={"ownedTags":owned,"referencedTags":refs,"strings":strings}
                else:
                    # Some hsdata snapshots contain multiple Entity records for one CardID.
                    # The CANT_ATTACK evidence is on the canonical record later in the stream.
                    existing={x["id"] for x in out[cid]["ownedTags"]}
                    for row in owned:
                        if row["id"]==227 and row["id"] not in existing:
                            out[cid]["ownedTags"].append(row)
                    existing_refs={x["id"] for x in out[cid]["referencedTags"]}
                    for row in refs:
                        if row["id"] not in existing_refs:
                            out[cid]["referencedTags"].append(row)
                    for tid,string_data in strings.items():
                        if tid not in out[cid]["strings"]: out[cid]["strings"][tid]=string_data
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
    elif cid not in ("GIL_188a","GIL_188b"):s["cost"]=0
    if kind in ("MINION","HERO","HERO_POWER"):
        if 47 in tags:s["attack"]=tags[47]
        elif kind=="MINION":s["attack"]=0
    if kind=="MINION" and 45 in tags:s["health"]=tags[45]
    if kind=="WEAPON":
        if 47 in tags:s["attack"]=tags[47]
        if 187 in tags:s["durability"]=tags[187]
        elif 45 in tags:s["durability"]=tags[45]
    if kind in ("HERO","HERO_POWER") and 292 in tags:s["armor"]=tags[292]
    if kind=="HERO" and 45 in tags:s["health"]=tags[45]
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
    if kind=="HERO":
        for f in ("attack","durability","race","races","spellSchool"):s.pop(f,None)
    if kind=="HERO_POWER":
        for f in ("armor","attack","durability","health","race","races","spellSchool"):s.pop(f,None)
    if cid=="GIL_504h":s["collectible"]=False
    if cid=="GIL_504":s["health"]=30
    return s
def api_text(s): return s.replace("\n","<br></br>").replace("\r\n","<br></br>").replace("\r","<br></br>")

def main():
    catalog=read(ROOT/"cards.json"); records={c["id"]:c for c in catalog["cards"]}
    assert len(records)==156
    research=read(ROOT/"sources/witchwood-research-v1.json")
    source_manifest=read(ROOT/"sources/witchwood-source-manifest.json")
    baseline_history_path=ROOT/"sources/baseline/data-history.json"
    baseline_history=read(baseline_history_path) if baseline_history_path.exists() else read(ROOT/"data/history.json")
    central=baseline_history
    events=central["events"]
    assert len(events["2018-04-13"])==156
    assert sum(len(v) for d,v in events.items() if d!="2018-04-13")==40
    launch=parse_entities(Path("/tmp/CardDefs-witchwood-launch.xml"),set(records))
    current_entities=parse_entities(Path("/tmp/CardDefs-witchwood-current.xml"),set(records))
    baseline_cards=read(ROOT/"sources/baseline/cards.json") if (ROOT/"sources/baseline/cards.json").exists() else copy.deepcopy(catalog)
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
        normalized_tags=copy.deepcopy(normalized.pop("nativeTags",[]))
        normalized.pop("referencedTags",None); normalized.pop("ownedTags",None); normalized.pop("nativeTagOrigins",None)
        baseline_tags=copy.deepcopy(baseline.pop("nativeTags",[]))
        baseline.pop("referencedTags",None); baseline.pop("ownedTags",None); baseline.pop("nativeTagOrigins",None)
        if cid=="GIL_152" and any(x.get("id")==227 for x in normalized_tags): baseline_tags.append({"id":227,"name":"공격 불가","value":1})
        normalized_tags.sort(key=lambda x:x["id"]); baseline_tags.sort(key=lambda x:x["id"])
        if normalized_tags!=baseline_tags:
            actual={x["id"]:x.get("value") for x in normalized_tags}
            expected={x["id"]:x.get("value") for x in baseline_tags}
            raise ValueError(f"{cid}: current tag mismatch missing={sorted(set(expected)-set(actual))} extra={sorted(set(actual)-set(expected))} changed={[(k,expected[k],actual[k]) for k in sorted(set(actual)&set(expected)) if actual[k]!=expected[k]]}")
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
    current_tags={}; current_refs={}; current_owned={}; current_origins={}
    for cid in records:
        legacy_rows=copy.deepcopy(original[cid].get("nativeTags",[]))
        if cid=="GIL_152" and not any(x.get("id")==227 for x in legacy_rows):
            legacy_rows.append({"id":227,"name":"공격 불가","value":1})
        legacy_rows.sort(key=lambda x:x["id"])
        current_tags[cid]=legacy_rows
        current_owned[cid]=named(current_entities[cid]["ownedTags"])
        current_refs[cid]=named(current_entities[cid]["referencedTags"])
        ref_ids={x["id"] for x in current_refs[cid]}
        owned_ids={x["id"] for x in current_owned[cid]}
        current_origins[cid]=[{"id":x["id"],"role":"referenced" if x["id"] in ref_ids else "owned" if x["id"] in owned_ids else "legacy-only"} for x in legacy_rows]
        if cid=="GIL_152":
            xml_tag=next((x for x in current_entities[cid]["ownedTags"] if x["id"]==227),None)
            if not xml_tag or xml_tag.get("value")!=1: raise ValueError("Current XML does not contain owned GIL_152 CANT_ATTACK=1")
        expected=copy.deepcopy(original[cid].get("nativeTags",[]))
        if cid=="GIL_152" and not any(x.get("id")==227 for x in expected): expected.append({"id":227,"name":"공격 불가","value":1})
        expected.sort(key=lambda x:x["id"])
        if current_tags[cid]!=expected: raise ValueError(f"{cid}: public legacy nativeTags changed beyond approved Tag227")
    if sum(len(v) for v in current_refs.values())!=25 or sum(bool(v) for v in current_refs.values())!=20:
        raise ValueError("Current referenced-tag role audit must resolve exactly 25 tags across 20 cards")
    # Preserve all current non-tag fields byte-for-byte at the JSON-value level.
    # Preserve all current non-tag fields byte-for-byte at the JSON-value level.
    for cid,card in records.items():
        src=read(ROOT/"sources/baseline/cards-data"/(cid+".json"))
        if src.get("schemaVersion")!=1 or src.get("mode") is None or not isinstance(src.get("artworkProvenance"),dict):
            raise ValueError(f"{cid}: legacy source metadata missing")
        if src["card"].get("portrait")!=original[cid].get("portrait"):raise ValueError(f"{cid}: portrait drift")
        initial=state_from(launch[cid],cid)
        initial["id"]=cid
        initial["dbfId"]=card["dbfId"]
        if "collectible" not in initial: initial["collectible"]=bool(old_current["collectible"])
        if initial["type"]=="WEAPON" and "durability" not in initial: initial["durability"]=0
        if initial["type"]=="HERO" and "armor" not in initial: initial["armor"]=0
        launch_owned=named(launch[cid]["ownedTags"])
        launch_refs=named(launch[cid]["referencedTags"])
        initial["ownedTags"]=copy.deepcopy(launch_owned)
        initial["referencedTags"]=copy.deepcopy(launch_refs)
        initial["nativeTags"]=sorted(copy.deepcopy(launch_owned+launch_refs),key=lambda x:x["id"])
        initial["nativeTagOrigins"]=[{"id":x["id"],"role":"referenced" if x["id"] in {r["id"] for r in launch_refs} else "owned"} for x in initial["nativeTags"]]
        first=corrected.get(RELEASE,{})
        # The old release row is a legacy current snapshot; never use it as launch state.
        old_current=copy.deepcopy(src["card"])
        timeline={RELEASE:{"state":initial,"ownedTags":named(launch[cid]["ownedTags"]),"referencedTags":named(launch[cid]["referencedTags"])}}
        # Confirmed gameplay changes, with full-state deltas built from launch forward.
        for day,changes in PATCHES.get(cid,[]):
            timeline.setdefault(day,{"changes":{},"sources":[],"eventKinds":[]})
            timeline[day]["changes"].update(copy.deepcopy(changes))
            timeline[day]["eventKinds"].append("gameplay")
        for day,changes in REPRESENTATION_PATCHES.get(cid,[]):
            timeline.setdefault(day,{"changes":{},"sources":[],"eventKinds":[],"representation":{}})
            clean=copy.deepcopy(changes)
            if "tagStorage" in clean or "nativeTagRoleChange" in clean:
                timeline[day]["representation"].update(clean)
                clean={k:v for k,v in clean.items() if k not in ("tagStorage","nativeTagRoleChange")}
            timeline[day]["changes"].update(clean)
            timeline[day]["eventKinds"].append("representation")
        # Existing race/school events retain only their confirmed logical deltas.
        for day,group in corrected.items():
            if day==RELEASE or cid not in group:continue
            entry=group[cid]
            changes={}
            if "races" in entry:
                changes["races"]=copy.deepcopy(entry["races"])
                changes["race"]=copy.deepcopy(entry.get("race",""))
            if "spellSchool" in entry:changes["spellSchool"]=entry["spellSchool"]
            if cid=="GIL_191" and day=="2021-03-26":changes["cost"]=4
            if cid=="GIL_663" and day=="2021-03-26":changes["cost"]=2
            if cid=="GIL_600" and day=="2021-03-26":changes["cost"]=0
            if cid=="GIL_667" and day=="2022-11-30":changes["health"]=5
            if changes:
                timeline.setdefault(day,{"changes":{},"sources":[],"eventKinds":[]})
                timeline[day]["changes"].update(changes)
                timeline[day]["eventKinds"].append("existing-confirmed")
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
        raw_current=current_entities[cid]["strings"].get("184",{}).get("locales",{}).get("koKR",{}).get("nativeRawText")
        if raw_current is not None: current_state["nativeRawText"]=copy.deepcopy(raw_current)
        latest=states[-1][1]
        undated={}
        for field,value in current_state.items():
            if field in latest and latest[field]!=value:
                undated[field]={"date":None,"before":copy.deepcopy(latest[field]),"after":copy.deepcopy(value),"reason":"current cache differs from dated confirmed events; no date inferred"}
        # Reconstruct dated raw tags from launch XML and confirmed field deltas only.
        owned_state={x["id"]:copy.deepcopy(x) for x in launch_owned}
        refs_state={x["id"]:copy.deepcopy(x) for x in launch_refs}
        current_owned_by_id={x["id"]:copy.deepcopy(x) for x in current_owned[cid]}
        current_refs_by_id={x["id"]:copy.deepcopy(x) for x in current_refs[cid]}
        tag_states={}
        def set_owned(tag_id,value):
            owned_state[tag_id]={"id":tag_id,"name":TAG_NAMES.get(tag_id,f"게임 태그 {tag_id}"),"value":copy.deepcopy(value)}
        def remove_owned(tag_id): owned_state.pop(tag_id,None)
        def flat_tags():
            merged={}
            for row in list(owned_state.values())+list(refs_state.values()): merged[row["id"]]=copy.deepcopy(row)
            return [merged[k] for k in sorted(merged)]
        for day in dates:
            changes=timeline[day].get("changes",{})
            for field,tag_id in (("cost",48),("attack",47),("health",45),("durability",187),("armor",292)):
                if field in changes: set_owned(tag_id,changes[field])
            if "spellSchool" in changes:
                school_id={v:k for k,v in SCHOOL.items()}.get(changes["spellSchool"])
                if school_id is not None: set_owned(1635,school_id)
            if "races" in changes:
                races=changes["races"]
                if cid=="GIL_584": set_owned(200,15)
                elif cid=="GIL_545" and day=="2018-08-03": remove_owned(200)
                elif cid=="GIL_534": set_owned(200,22)
                elif "ALL" in races: set_owned(200,26)
                if "UNDEAD" in races: set_owned(2534,1)
            if "nativeTags" in changes:
                owned_state={x["id"]:copy.deepcopy(x) for x in changes["nativeTags"]}
                refs_state={}
            rep=timeline[day].get("representation",{})
            if rep.get("tagStorage")=="DURABILITY_187_TO_HEALTH_45":
                raw_after={
                 "GIL_596":[(32,1),(45,4),(47,3),(48,8),(183,1125),(199,5),(202,7),(203,3),(321,1)],
                 "GIL_653":[(32,1),(45,2),(47,2),(48,2),(183,1125),(199,10),(202,7),(203,1),(217,1),(321,1)],
                 "GIL_672":[(45,2),(47,2),(48,4),(183,1125),(199,7),(202,7),(203,4),(321,1),(685,1)]
                }[cid]
                owned_state={tid:{"id":tid,"name":TAG_NAMES.get(tid,f"게임 태그 {tid}"),"value":value} for tid,value in raw_after}
            if rep.get("nativeTagRoleChange"):
                for tid_text,role in rep["nativeTagRoleChange"].items():
                    tid=int(tid_text)
                    if role=="owned":
                        row=refs_state.pop(tid,None) or current_refs_by_id.get(tid) or current_owned_by_id.get(tid)
                        if row: owned_state[tid]=copy.deepcopy(row)
                    elif role=="referenced":
                        row=owned_state.pop(tid,None) or current_refs_by_id.get(tid) or current_owned_by_id.get(tid)
                        if row: refs_state[tid]=copy.deepcopy(row)
            flat=flat_tags()
            roles=[{"id":tid,"role":"owned"} for tid in sorted(owned_state)]+[{"id":tid,"role":"referenced"} for tid in sorted(refs_state)]
            tag_states[day]={"nativeTags":flat,"ownedTags":[copy.deepcopy(owned_state[k]) for k in sorted(owned_state)],
                             "referencedTags":[copy.deepcopy(refs_state[k]) for k in sorted(refs_state)],"nativeTagOrigins":sorted(roles,key=lambda x:(x["id"],x["role"]))}
        for day,hstate in states:
            hstate["nativeTags"]=copy.deepcopy(tag_states[day]["nativeTags"])
            hstate["ownedTags"]=copy.deepcopy(tag_states[day]["ownedTags"])
            hstate["referencedTags"]=copy.deepcopy(tag_states[day]["referencedTags"])
            hstate["nativeTagOrigins"]=copy.deepcopy(tag_states[day]["nativeTagOrigins"])
        # Build fully self-contained historical overrides against the public current card.
        revisions=[]
        for i,(day,hstate) in enumerate(states):
            changes={k:copy.deepcopy(v) for k,v in hstate.items()}
            if "text" in changes: changes["text"]=api_text(changes["text"])

            removed=sorted(k for k in current_state if k not in hstate)
            rev={"from":day,"changes":changes,"eventKinds":copy.deepcopy(timeline[day].get("eventKinds",[]))}
            if timeline[day].get("representation"):rev["representation"]=copy.deepcopy(timeline[day]["representation"])
            if timeline[day].get("sources"):rev["sources"]=copy.deepcopy(timeline[day]["sources"])
            if i+1<len(states):rev["before"]=states[i+1][0]
            if removed:rev["removedFields"]=removed
            revisions.append(rev)
        dbf=str(old_current["dbfId"])
        # Public API source retains old metadata and card wrapper; only adds schema-v2 audit material.
        src["schemaVersion"]=2
        src["initialSpec"]=copy.deepcopy(initial)
        src["patches"]=[{"date":rev["from"],"changes":copy.deepcopy(rev["changes"]),"removedFields":copy.deepcopy(rev.get("removedFields",[])),
                         "eventKinds":copy.deepcopy(rev.get("eventKinds",[])),"representation":copy.deepcopy(rev.get("representation",{})),
                         "sources":copy.deepcopy(rev.get("sources",[]))} for rev in revisions[1:]]
        src["current"]=copy.deepcopy(old_current)
        src["card"]["nativeTags"]=copy.deepcopy(current_tags[cid])
        src["card"]["referencedTags"]=copy.deepcopy(current_refs[cid])
        src["card"]["ownedTags"]=copy.deepcopy(current_owned[cid])
        src["card"]["nativeTagOrigins"]=copy.deepcopy(current_origins[cid])
        src["current"]["nativeTags"]=copy.deepcopy(current_tags[cid])
        src["current"]["referencedTags"]=copy.deepcopy(current_refs[cid])
        src["current"]["ownedTags"]=copy.deepcopy(current_owned[cid])
        src["current"]["nativeTagOrigins"]=copy.deepcopy(current_origins[cid])
        if raw_current is not None:
            src["nativeRawText"]=copy.deepcopy(raw_current)
            src["current"]["nativeRawText"]=copy.deepcopy(raw_current)
            src["card"]["nativeRawText"]=copy.deepcopy(raw_current)
        src["history"]=copy.deepcopy(revisions)
        src["observations"]={"undated":undated,"research":[copy.deepcopy(x) for x in research["observations"] if cid in x.get("cardIds",[])]}
        # Date-first canonical snapshots are real top-level YYYY-MM-DD keys in this same file.
        for rev in revisions:
            day=rev["from"]
            snapshot=copy.deepcopy(rev["changes"])
            snapshot["removedFields"]=copy.deepcopy(rev.get("removedFields",[]))
            snapshot["eventKinds"]=copy.deepcopy(timeline[day].get("eventKinds",[]))
            if timeline[day].get("representation"): snapshot["representation"]=copy.deepcopy(timeline[day]["representation"])
            if timeline[day].get("sources"): snapshot["sources"]=copy.deepcopy(timeline[day]["sources"])
            src[day]=snapshot
        src["_meta"]={"schemaVersion":2,"timezone":"Asia/Seoul","releasedAt":RELEASE,
                      "source":"HearthSim hsdata immutable launch XML 6317434bee453ec6e8267cbf45277c0a13da90f8",
                      "launchOwnedTags":copy.deepcopy(launch_owned),"launchReferencedTags":copy.deepcopy(launch_refs),
                      "currentOwnedTags":copy.deepcopy(current_owned[cid]),
                      "currentReferencedTags":copy.deepcopy(current_refs[cid]),
                      "currentNativeTagOrigins":copy.deepcopy(current_origins[cid]),
                      "launchStrings":copy.deepcopy(launch[cid]["strings"]),
                      "currentStrings":copy.deepcopy(current_entities[cid]["strings"]),
                      "portrait":copy.deepcopy(old_current.get("portrait")),"art":copy.deepcopy(old_current.get("art")),
                      "relations":copy.deepcopy(old_current.get("relations",old_current.get("relationships",[]))),
                      "relationships":copy.deepcopy(research["relationships"]),"sourceManifest":copy.deepcopy(source_manifest),
                      "current":copy.deepcopy(src["current"]),
                      "mode":src["mode"],"artworkProvenance":copy.deepcopy(src["artworkProvenance"]),
                      "researchObservationIds":[x["id"] for x in research["observations"] if cid in x.get("cardIds",[])]}
        write(ROOT/"data"/(cid+".json"),src)
        # cards.json/render.json preserve existing fields; approved Tag addition only.
        records[cid]["nativeTags"]=copy.deepcopy(current_tags[cid])
        records[cid]["referencedTags"]=copy.deepcopy(current_refs[cid])
        records[cid]["ownedTags"]=copy.deepcopy(current_owned[cid])
        records[cid]["nativeTagOrigins"]=copy.deepcopy(current_origins[cid])
        # Legacy history uses a full initialSpec and date patches.
        legacy_patches=[]
        for i,rev in enumerate(revisions[1:]):
            legacy_patches.append({"date":rev["from"],"changes":copy.deepcopy(rev["changes"]),"removedFields":copy.deepcopy(rev.get("removedFields",[])),
                                  "eventKinds":copy.deepcopy(rev.get("eventKinds",[])),"representation":copy.deepcopy(rev.get("representation",{}))})
    catalog["cards"]=list(records.values())
    # Generate compatibility indexes and a separate explicit date-first canonical source.
    public_history={"schema":2,"timezone":"Asia/Seoul","format":"date-first-delta","events":{RELEASE:{}},
                    "sourceManifest":copy.deepcopy(source_manifest),
                    "observations":copy.deepcopy(research["observations"]),
                    "schemaPolicy":copy.deepcopy(research["schemaPolicy"]),
                    "rawTagAudit":copy.deepcopy(research["rawTagAudit"]),
                    "editorial":copy.deepcopy(research["editorial"]),
                    "relationships":copy.deepcopy(research["relationships"])}
    render=[]
    legacy={"schema":1,"set":"The Witchwood","cards":{}}
    for card in catalog["cards"]:
        cid=card["id"]; src=read(ROOT/"data"/(cid+".json")); dbf=str(card["dbfId"])
        legacy["cards"][dbf]={"id":cid,"initialSpec":src["initialSpec"],"patches":src["patches"]}
        date_keys=sorted(k for k in src if DATE.fullmatch(k))
        if not date_keys or date_keys[0]!=RELEASE: raise ValueError(f"{cid}: missing top-level date-first release snapshot")
        initial=copy.deepcopy(src[RELEASE])
        public_history["events"][RELEASE][cid]=initial
        previous=copy.deepcopy(initial)
        for day in date_keys[1:]:
            snapshot=copy.deepcopy(src[day])
            removed=list(snapshot.pop("removedFields",[]))
            event_kinds=snapshot.pop("eventKinds",[])
            representation=snapshot.pop("representation",{})
            event_sources=snapshot.pop("sources",[])
            following=copy.deepcopy(snapshot)
            for field in removed: following.pop(field,None)
            delta={field:copy.deepcopy(value) for field,value in following.items()
                   if field not in previous or previous[field]!=value}
            removed_delta=sorted(field for field in previous if field not in following)
            if delta or removed_delta or event_kinds or representation:
                public_history["events"].setdefault(day,{})[cid]={"changes":delta,"removedFields":removed_delta,
                    "eventKinds":event_kinds,"representation":representation,"sources":event_sources}
            previous=following
        r={k:copy.deepcopy(v) for k,v in card.items()}
        r["history"]=copy.deepcopy(src["history"])
        r["referencedTags"]=copy.deepcopy(src["current"].get("referencedTags",[]))
        render.append(r)
    write(ROOT/"cards.json",catalog,True)
    write(ROOT/"render.json",{"schema":1,"set":"The Witchwood","cards":render},True)
    write(ROOT/"history.json",legacy,True)
    write(ROOT/"data/history.json",public_history)
    write(ROOT/"sources/witchwood-history-v2.json",public_history)
    print(json.dumps({"cards":len(records),"release":RELEASE,"legacyEvents":40,"correctedUndead":25,
                      "confirmedGameplayPatchEvents":sum(len(v) for v in PATCHES.values()),
                      "currentApprovedTagAddition":"GIL_152:227=1","generated":"cards/render/history + date-first source"},ensure_ascii=False))
if __name__=="__main__":main()
