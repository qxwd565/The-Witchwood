#!/usr/bin/env python3
"""Synchronize compatibility APIs from the authoritative sparse per-card date-first sources."""
from __future__ import annotations
import copy, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RELEASE="2018-04-13"
DATE=re.compile(r"^\d{4}-\d{2}-\d{2}$")
TAG_FIELDS={"nativeTags","ownedTags","referencedTags","nativeTagOrigins"}
META_FIELDS={"removedFields","rawTagDelta","eventKinds","representation","sources"}

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def write(path,obj,compact=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(obj,ensure_ascii=False,separators=(",",":") if compact else None,indent=None if compact else 2)+"\n"
    if not path.exists() or path.read_text(encoding="utf-8")!=payload:
        path.write_text(payload,encoding="utf-8",newline="\n")
        return True
    return False

def tag_index(rows):
    return {int(x["id"]):copy.deepcopy(x) for x in rows}

def flattened(owned,referenced):
    merged={}
    for role,rows in (("owned",owned),("referenced",referenced)):
        for row in rows:
            tid=int(row["id"])
            if tid in merged: raise ValueError(f"duplicate tag role collision: {tid}")
            merged[tid]=copy.deepcopy(row)
    native=[merged[k] for k in sorted(merged)]
    origins=[{"id":int(row["id"]),"role":role} for role,rows in (("owned",owned),("referenced",referenced)) for row in rows]
    origins.sort(key=lambda x:(x["id"],x["role"]))
    return native,origins

def apply_raw_delta(state,day,rows):
    for event in rows:
        role=event["role"]
        if role not in ("ownedTags","referencedTags"): raise ValueError(f"{day}: invalid raw tag role {role}")
        before=event.get("before","ABSENT")
        after=event.get("after","ABSENT")
        current=tag_index(state.get(role,[]))
        tid=int(event["id"])
        actual=current.get(tid,"ABSENT")
        if actual!=before:
            raise ValueError(f"{day} Tag{tid} {role} before mismatch: {actual!r} != {before!r}")
        if after=="ABSENT": current.pop(tid,None)
        else:
            if not isinstance(after,dict) or int(after.get("id",tid))!=tid:
                raise ValueError(f"{day} Tag{tid}: malformed raw after value {after!r}")
            current[tid]=copy.deepcopy(after)
        state[role]=[current[k] for k in sorted(current)]
    native,origins=flattened(state.get("ownedTags",[]),state.get("referencedTags",[]))
    state["nativeTags"]=native
    state["nativeTagOrigins"]=origins

def card_history(source):
    date_keys=sorted(k for k in source if DATE.fullmatch(k))
    if not date_keys or date_keys[0]!=RELEASE:
        raise ValueError(f"{source.get('card',{}).get('id')}: missing full release state")
    initial=copy.deepcopy(source[RELEASE])
    for meta_field in META_FIELDS: initial.pop(meta_field,None)
    if any(k in initial for k in META_FIELDS):
        raise ValueError(f"{source['card']['id']}: release state contains event metadata")
    state=copy.deepcopy(initial)
    full_states=[]
    events={}
    for day in date_keys:
        if day==RELEASE:
            full=copy.deepcopy(state)
            events[day]=copy.deepcopy(initial)
        else:
            delta=copy.deepcopy(source[day])
            removed=list(delta.pop("removedFields",[]))
            raw_delta=delta.pop("rawTagDelta",[])
            event_kinds=delta.pop("eventKinds",[])
            representation=delta.pop("representation",{})
            sources=delta.pop("sources",[])
            for field,value in delta.items():
                if field in TAG_FIELDS: raise ValueError(f"{source['card']['id']} {day}: full tag snapshot in sparse date row")
                state[field]=copy.deepcopy(value)
            for field in removed:
                state.pop(field,None)
            if raw_delta: apply_raw_delta(state,day,raw_delta)
            full=copy.deepcopy(state)
            events[day]={"changes":copy.deepcopy(delta),"removedFields":removed,"rawTagDelta":raw_delta,
                         "eventKinds":event_kinds,"representation":representation,"sources":sources}
        native,origins=flattened(full.get("ownedTags",[]),full.get("referencedTags",[]))
        full["nativeTags"]=native
        full["nativeTagOrigins"]=origins
        full_states.append((day,full,copy.deepcopy(source[day])))
    current=copy.deepcopy(source["current"])
    current_fields={k:copy.deepcopy(v) for k,v in current.items() if k not in TAG_FIELDS}
    revisions=[]
    for i,(day,full,sparse) in enumerate(full_states):
        removed=sorted(k for k in current_fields if k not in full)
        revision={"from":day,"changes":copy.deepcopy(full),
                  "eventKinds":copy.deepcopy(sparse.get("eventKinds",[]))}
        if sparse.get("representation"): revision["representation"]=copy.deepcopy(sparse["representation"])
        if sparse.get("sources"): revision["sources"]=copy.deepcopy(sparse["sources"])
        if i+1<len(full_states): revision["before"]=full_states[i+1][0]
        if removed: revision["removedFields"]=removed
        revisions.append(revision)
    patches=[]
    for rev in revisions[1:]:
        patches.append({"date":rev["from"],"changes":copy.deepcopy(rev["changes"]),
                        "removedFields":copy.deepcopy(rev.get("removedFields",[])),
                        "eventKinds":copy.deepcopy(rev.get("eventKinds",[])),
                        "representation":copy.deepcopy(rev.get("representation",{})),
                        "sources":copy.deepcopy(rev.get("sources",[]))})
    source["initialSpec"]=copy.deepcopy(initial)
    source["history"]=copy.deepcopy(revisions)
    source["patches"]=copy.deepcopy(patches)
    source["_meta"]["schemaVersion"]=3
    source["_meta"]["dateFirstFormat"]="sparse-delta-v3"
    return source,events,revisions,patches

def main():
    catalog=read(ROOT/"cards.json")
    records={x["id"]:x for x in catalog["cards"]}
    files=sorted((ROOT/"data").glob("GIL_*.json"))
    if len(files)!=156 or set(p.stem for p in files)!=set(records):
        raise ValueError("Sparse date-first source must contain all 156 Witchwood card files")
    public={"schema":3,"timezone":"Asia/Seoul","format":"date-first-delta-v3","events":{RELEASE:{}},
            "sourceManifest":read(ROOT/"sources/witchwood-source-manifest.json"),
            "observations":None,"gameplayEvidence":None}
    research=read(ROOT/"sources/witchwood-research-v1.json")
    public["observations"]=[]
    for src_path in files:
        src=read(src_path)
        src,events,revisions,patches=card_history(src)
        cid=src["card"]["id"]
        public["events"][RELEASE][cid]=events[RELEASE]
        for day,row in events.items():
            if day==RELEASE: continue
            public["events"].setdefault(day,{})[cid]=row
        expected={x["id"] for x in public["sourceManifest"].get("entries",[])}
        if not src.get("initialSpec") or not src.get("history"): raise ValueError(f"{cid}: adapter failed to build history")
        src_path.write_text(json.dumps(src,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    # All 13 research groups and nine additional undated records are carried by the card files.
    obs_map={}
    for path in files:
        src=read(path)
        for group in src.get("observations",{}).get("research",[]):
            obs_map[group["id"]]=copy.deepcopy(group)
    if len(obs_map)!=13: raise ValueError(f"Expected 13 research observation groups, got {len(obs_map)}")
    public["observations"]=[obs_map[k] for k in sorted(obs_map)]
    public["gameplayEvidence"]=read(ROOT/"data/history.json").get("gameplayEvidence",{})
    public["schemaPolicy"]=research["schemaPolicy"]
    public["rawTagAudit"]=research["rawTagAudit"]
    public["editorial"]=research["editorial"]
    public["relationships"]=research["relationships"]
    legacy={"schema":1,"set":"The Witchwood","cards":{}}
    render=[]
    for card in catalog["cards"]:
        cid=card["id"]
        src=read(ROOT/"data"/(cid+".json"))
        dbf=str(card["dbfId"])
        legacy["cards"][dbf]={"id":cid,"initialSpec":copy.deepcopy(src["initialSpec"]),"patches":copy.deepcopy(src["patches"])}
        rendered=copy.deepcopy(card)
        rendered["history"]=copy.deepcopy(src["history"])
        rendered["referencedTags"]=copy.deepcopy(src["current"].get("referencedTags",[]))
        rendered["ownedTags"]=copy.deepcopy(src["current"].get("ownedTags",[]))
        rendered["nativeTagOrigins"]=copy.deepcopy(src["current"].get("nativeTagOrigins",[]))
        render.append(rendered)
    write(ROOT/"render.json",{"schema":1,"set":"The Witchwood","cards":render},True)
    write(ROOT/"history.json",legacy,True)
    write(ROOT/"data/history.json",public)
    write(ROOT/"sources/witchwood-history-v2.json",public)
    print(json.dumps({"cards":len(records),"releaseCards":len(public["events"][RELEASE]),
                      "dateRows":sum(len(v) for k,v in public["events"].items() if k!=RELEASE),
                      "sparseSource":"data/GIL_*.json","adapter":"cumulative sparse-to-legacy",
                      "observations":len(public["observations"])},ensure_ascii=False))
if __name__=="__main__": main()
