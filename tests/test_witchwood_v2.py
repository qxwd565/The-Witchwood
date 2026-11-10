import base64, copy, gzip, json, re, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RELEASE="2018-04-13"
DATE=re.compile(r"^\d{4}-\d{2}-\d{2}$")
def read(p): return json.loads(p.read_text(encoding="utf-8"))
def evidence(path):
    line=(ROOT/path).read_text(encoding="utf-8").splitlines()[-1].strip()
    return json.loads(gzip.decompress(base64.b64decode(line)))
def value(rows,tid):
    row=next((x for x in rows if int(x["id"])==int(tid)),None)
    return "ABSENT" if row is None else str(row.get("value")) if "value" in row else "NO_VALUE"
class WitchwoodSparseHistoryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.catalog=read(ROOT/"cards.json")["cards"]
  cls.render=read(ROOT/"render.json")["cards"]
  cls.legacy=read(ROOT/"history.json")["cards"]
  cls.central=read(ROOT/"data/history.json")
  cls.research=read(ROOT/"sources/witchwood-research-v1.json")
  cls.manifest=read(ROOT/"sources/witchwood-source-manifest.json")
  cls.audit=evidence("sources/witchwood-independent-audit-v2.json.gz.b64")
  cls.obs_evidence=evidence("sources/witchwood-observations-evidence.json.gz.b64")
  cls.event_evidence=evidence("sources/witchwood-event-evidence.json.gz.b64")
  cls.baseline={x["id"]:x for x in read(ROOT/"sources/baseline/cards.json")["cards"]}
  cls.data={p.stem:read(p) for p in (ROOT/"data").glob("GIL_*.json")}
  cls.cards={x["id"]:x for x in cls.catalog}
  cls.rendered={x["id"]:x for x in cls.render}
 @staticmethod
 def state(src,day):
  return next(x["changes"] for x in src["history"] if x["from"]==day)
 def apply_sparse(self,state,sparse,day):
  for field,val in sparse.items():
   if field in ("removedFields","rawTagDelta","eventKinds","representation","sources"): continue
   self.assertNotEqual(state.get(field,"__MISSING__"),val,(day,field,"not a real delta"))
   state[field]=copy.deepcopy(val)
  for event in sparse.get("rawTagDelta",[]):
   if event.get("operation")=="roleTransfer":
    tid=int(event["id"]); from_role=event["from"]; to_role=event["to"]; val=copy.deepcopy(event["value"])
    self.assertEqual((from_role,to_role),("referencedTags","ownedTags"),(day,tid,"role transfer"))
    rows={int(x["id"]):copy.deepcopy(x) for x in state.get(from_role,[])}
    if tid in rows: self.assertEqual(rows[tid],val)
    rows.pop(tid,None); state[from_role]=[rows[k] for k in sorted(rows)]
    target={int(x["id"]):copy.deepcopy(x) for x in state.get(to_role,[])}
    self.assertTrue(tid not in target or target[tid]==val,(day,tid,"role transfer collision"))
    target[tid]=val; state[to_role]=[target[k] for k in sorted(target)]
    continue
   role=event["role"]; rows={int(x["id"]):copy.deepcopy(x) for x in state.get(role,[])}; tid=int(event["id"])
   self.assertEqual(rows.get(tid,"ABSENT"),event.get("before","ABSENT"),(day,tid,"raw before"))
   after=event.get("after","ABSENT")
   if after=="ABSENT": rows.pop(tid,None)
   else: rows[tid]=copy.deepcopy(after)
   state[role]=[rows[k] for k in sorted(rows)]
  for field in sparse.get("removedFields",[]):
   self.assertIn(field,state,(day,field,"remove absent field"))
   state.pop(field)
  merged={}
  for role in ("ownedTags","referencedTags"):
   for row in state.get(role,[]):
    self.assertNotIn(int(row["id"]),merged,(day,row["id"],"tag role collision"))
    merged[int(row["id"])]=copy.deepcopy(row)
  state["nativeTags"]=[merged[k] for k in sorted(merged)]
  state["nativeTagOrigins"]=sorted([{"id":int(x["id"]),"role":"owned" if role=="ownedTags" else "referenced"} for role in ("ownedTags","referencedTags") for x in state.get(role,[])],key=lambda x:(x["id"],x["role"]))
  return state
 def test_156_cards_immutable_current_compatibility(self):
  self.assertEqual(len(self.cards),156); self.assertEqual(len(self.render),156); self.assertEqual(len(self.data),156)
  self.assertEqual(len(self.legacy),156)
  self.assertEqual(sum(bool(x.get("collectible")) for x in self.cards.values()),135)
  self.assertEqual(sum(not bool(x.get("collectible")) for x in self.cards.values()),21)
  for cid,base in self.baseline.items():
   card=self.cards[cid]; source=self.data[cid]
   for key,val in base.items():
    if key!="nativeTags": self.assertEqual(card.get(key),val,(cid,key))
   expected=copy.deepcopy(base.get("nativeTags",[]))
   if cid=="GIL_152" and not any(x["id"]==227 for x in expected): expected.append({"id":227,"name":"공격 불가","value":1})
   self.assertEqual(sorted(card.get("nativeTags",[]),key=lambda x:x["id"]),sorted(expected,key=lambda x:x["id"]),cid)
   base_data=read(ROOT/"sources/baseline/cards-data"/(cid+".json"))
   self.assertEqual(source["mode"],base_data["mode"]); self.assertEqual(source["artworkProvenance"],base_data["artworkProvenance"])
   self.assertEqual(source["card"]["portrait"],base.get("portrait")); self.assertEqual(source["card"]["art"],base.get("art"))
   self.assertEqual(source["_meta"]["mode"],source["mode"]); self.assertEqual(source["_meta"]["artworkProvenance"],source["artworkProvenance"])
 def test_51_independent_raw_replay_diffs(self):
  self.assertEqual(len(self.audit["rawReplayDiffs"]),51)
  for diff in self.audit["rawReplayDiffs"]:
   state=self.state(self.data[diff["id"]],diff["day"])
   self.assertEqual(value(state[diff["role"]],diff["tag"]),diff["expected"],(diff["id"],diff["day"],diff["tag"]))
 def test_existing_40_raw_before_after_deltas(self):
  self.assertEqual(len(self.audit["existingRawDelta40"]),40)
  for event in self.audit["existingRawDelta40"]:
   state=self.state(self.data[event["id"]],event["date"])
   undated={str(x["tagId"]) for x in self.data[event["id"]]["observations"].get("undatedRawTags",[])}
   for tid,change in event["rawDelta"].items():
    if str(tid) in undated: continue
    self.assertEqual(value(state["ownedTags"],tid),change["after"],(event["id"],event["date"],tid))
 def test_14_event_archive_before_after_raw_tags(self):
  self.assertEqual(len(self.event_evidence["missingGameplayEvents"]),14)
  undated={(x["id"],int(x["confirmedTagId"]),x["role"]+"Tags") for x in self.audit["extraUndatedEvidence"]["observations"]}
  for cid,src in self.data.items():
   for x in src["observations"].get("undatedRawTags",[]): undated.add((cid,int(x["tagId"]),x["role"]))
  def tagmap(rows): return {str(x["id"]):str(x.get("value")) for x in rows if "value" in x}
  for event in self.event_evidence["missingGameplayEvents"]:
   cid=event["id"]; day=event["proposedKoreanDay"]; revisions=self.data[cid]["history"]
   after=next(x["changes"] for x in revisions if x["from"]==day)
   prior=[x for x in revisions if x["from"]<day]
   before=prior[-1]["changes"] if prior else self.data[cid]["initialSpec"]
   for role in ("ownedTags","referencedTags"):
    before_map=event["archiveBefore"].get(role,{})
    after_map=event["archiveAfter"].get(role,{})
    actual_before=tagmap(before.get(role,[])); actual_after=tagmap(after.get(role,[]))
    for tid in set(before_map)|set(after_map):
     if before_map.get(tid,"ABSENT")==after_map.get(tid,"ABSENT") or (cid,int(tid),role) in undated: continue
     self.assertEqual(actual_before.get(str(tid),"ABSENT"),before_map.get(tid,"ABSENT"),(cid,day,role,tid,"archive before"))
     self.assertEqual(actual_after.get(str(tid),"ABSENT"),after_map.get(tid,"ABSENT"),(cid,day,role,tid,"archive after"))
  for item in self.audit["extraUndatedEvidence"]["observations"]:
   rows=self.data[item["id"]]["observations"]["undatedRawTags"]
   self.assertTrue(any(x["findingId"]==item["findingId"] and x["tagId"]==item["confirmedTagId"] and x["before"]==item["before"] and x["after"]==item["after"] for x in rows),item["id"]+":"+item["findingId"])
   role=item["role"]+"Tags"; tid=int(item["confirmedTagId"])
   role_transfers=[]
   for day in (k for k in self.data[item["id"]] if DATE.fullmatch(k) and k!=RELEASE):
    for event in self.data[item["id"]][day].get("rawTagDelta",[]):
     if event.get("operation")=="roleTransfer" and int(event["id"])==tid and event.get("from")==role and day=="2026-07-22":
      role_transfers.append((day,event))
     else:
      self.assertFalse(event.get("role")==role and int(event["id"])==tid,(item["id"],day,tid,"undated promoted"))
   if item["findingId"]=="WITCH-BAL-R005":
    self.assertEqual(len(role_transfers),1,(item["id"],tid,"dated role transfer missing"))
   else:
    self.assertEqual(role_transfers,[])
 def test_40_existing_raw_delta_before_after_values(self):
  self.assertEqual(len(self.audit["existingRawDelta40"]),40)
  for event in self.audit["existingRawDelta40"]:
   cid=event["id"]; day=event["date"]; revisions=self.data[cid]["history"]
   after=next(x["changes"] for x in revisions if x["from"]==day)
   prior=[x for x in revisions if x["from"]<day]
   before=prior[-1]["changes"] if prior else self.data[cid]["initialSpec"]
   undated={str(x["tagId"]) for x in self.data[cid]["observations"].get("undatedRawTags",[])}
   for tid,change in event["rawDelta"].items():
    if str(tid) in undated: continue
    self.assertEqual(value(before["ownedTags"],tid),change["before"],(cid,day,tid,"before"))
    self.assertEqual(value(after["ownedTags"],tid),change["after"],(cid,day,tid,"after"))
 def test_22_initial_logical_fields(self):
  self.assertEqual(len(self.audit["initialLogicalDiffs"]),22)
  for row in self.audit["initialLogicalDiffs"]:
   initial=self.data[row["id"]]["initialSpec"]
   self.assertEqual(initial.get(row["field"],"ABSENT"),row["expected"],(row["id"],row["field"]))
   for revision in self.data[row["id"]]["history"]:
    self.assertEqual(revision["changes"].get(row["field"],"ABSENT"),row["expected"],(row["id"],revision["from"],row["field"]))
  noncollectible={x["id"] for x in self.audit["initialLogicalDiffs"] if x["field"]=="collectible"}
  self.assertEqual(len(noncollectible),15)
  for cid in noncollectible: self.assertIs(self.data[cid]["initialSpec"]["collectible"],False)
  empty_text={x["id"] for x in self.audit["initialLogicalDiffs"] if x["field"]=="text"}
  self.assertEqual(len(empty_text),7)
  for cid in empty_text: self.assertEqual(self.data[cid]["initialSpec"]["text"],"")
  self.assertNotIn("collectible",self.data["GIL_191t"]["observations"]["undated"])
 def test_every_sparse_date_row_is_a_real_delta_and_replays(self):
  intervals=0
  for cid,src in self.data.items():
   days=sorted(k for k in src if DATE.fullmatch(k))
   self.assertTrue(days and days[0]==RELEASE,cid)
   state=copy.deepcopy(src[RELEASE])
   self.assertIn("nativeTags",state); self.assertIn("ownedTags",state); self.assertIn("referencedTags",state)
   self.assertEqual(state,src["initialSpec"],cid+":release initialSpec")
   for day in days[1:]:
    sparse=src[day]
    self.assertFalse(any(k in sparse for k in ("id","dbfId","name","nativeTags","ownedTags","referencedTags","nativeTagOrigins")),(cid,day,"full snapshot leaked"))
    state=self.apply_sparse(state,sparse,day)
    expected=self.state(src,day)
    for field in ("type","cardClass","rarity","collectible","cost","attack","health","durability","armor","text","nativeRawText","races","race","spellSchool","nativeTags","ownedTags","referencedTags","nativeTagOrigins"):
     self.assertEqual(state.get(field,"ABSENT"),expected.get(field,"ABSENT"),(cid,day,field))
    intervals+=1
   self.assertEqual(days,sorted(x["from"] for x in src["history"]),cid+":date/history parity")
  self.assertEqual(intervals,63)
 def test_219_segments_are_156_release_plus_63_dated_followups(self):
  total=0
  for cid,src in self.data.items():
   current=copy.deepcopy(self.rendered[cid])
   dbf=str(src["current"]["dbfId"])
   self.assertEqual(self.legacy[dbf]["initialSpec"],src["initialSpec"])
   self.assertEqual(self.legacy[dbf]["patches"],src["patches"])
   for revision in src["history"]:
    restored=copy.deepcopy(current); restored.update(copy.deepcopy(revision["changes"]))
    for field in revision.get("removedFields",[]): restored.pop(field,None)
    for field in ("type","cardClass","rarity","collectible","cost","attack","health","durability","armor","text","nativeRawText","races","race","spellSchool","nativeTags","ownedTags","referencedTags","nativeTagOrigins"):
     self.assertEqual(restored.get(field,"ABSENT"),revision["changes"].get(field,"ABSENT"),(cid,revision["from"],field))
    total+=1
  self.assertEqual(total,219)
  self.assertEqual(total,156+63)
  dated_gameplay=sum(1 for cards in self.central["events"].values() for row in cards.values() if set(row.get("eventKinds",[])) & {"gameplay","existing-confirmed"})
  dated_representation=sum(1 for cards in self.central["events"].values() for row in cards.values() if "representation" in row.get("eventKinds",[]))
  self.assertEqual(dated_gameplay,53)
  self.assertEqual(dated_representation,10)
  self.assertEqual(dated_gameplay+dated_representation,63)
  self.assertEqual(sum(1 for group in self.central["observations"] for x in group.get("extraUndatedEvidence",[]) if x["findingId"]=="WITCH-BAL-R005"),2)
 def test_135_21_collectible_partition_at_release_and_every_global_date(self):
  states={cid:copy.deepcopy(src["initialSpec"]) for cid,src in self.data.items()}
  dates=sorted({day for src in self.data.values() for day in src if DATE.fullmatch(day)})
  for day in dates:
   for cid,src in self.data.items():
    if day==RELEASE: continue
    sparse=src.get(day)
    if sparse is not None: states[cid]=self.apply_sparse(copy.deepcopy(states[cid]),sparse,day)
   self.assertEqual(sum(bool(x.get("collectible")) for x in states.values()),135,day)
   self.assertEqual(sum(not bool(x.get("collectible")) for x in states.values()),21,day)
 def test_sparse_canonical_is_the_build_input(self):
  self.assertEqual(self.central["schema"],3); self.assertEqual(self.central["format"],"date-first-delta-v3")
  self.assertEqual(len(self.central["events"][RELEASE]),156)
  self.assertEqual(sum(len(v) for d,v in self.central["events"].items() if d!=RELEASE),63)
  for cid,src in self.data.items():
   for day in sorted(k for k in src if DATE.fullmatch(k) and k!=RELEASE):
    event=self.central["events"][day][cid]
    self.assertEqual(event.get("rawTagDelta",[]),src[day].get("rawTagDelta",[]))
    self.assertEqual(event.get("removedFields",[]),src[day].get("removedFields",[]))
    for field,val in src[day].items():
     if field not in ("rawTagDelta","removedFields","eventKinds","representation","sources"): self.assertEqual(event["changes"].get(field),val,(cid,day,field))
 def test_all_13_observation_groups_and_9_extra_undated_records(self):
  self.assertEqual(len(self.research["observations"]),13)
  self.assertEqual(len(self.obs_evidence),13)
  extra=[x for group in self.central["observations"] for x in group.get("extraUndatedEvidence",[])]
  self.assertEqual(len(extra),9)
  self.assertTrue(all(x.get("day") is None for x in extra))
  self.assertEqual(sum(x["findingId"]=="WITCH-BAL-R011" for x in extra),4)
  self.assertEqual(sum(x["findingId"]=="WITCH-BAL-R013" for x in extra),3)
  self.assertEqual(sum(x["findingId"]=="WITCH-BAL-R005" for x in extra),2)
  self.assertEqual(len(self.central["observations"]),13)
  self.assertEqual(self.central["sourceManifest"],self.manifest)
  self.assertEqual(len(self.manifest["entries"]),40)
 def test_14_missing_40_existing_and_10_representation_events_are_separate(self):
  self.assertEqual(len(self.event_evidence["missingGameplayEvents"]),14)
  self.assertEqual(len(self.event_evidence["existingLaterEventChecks"]),40)
  self.assertEqual(len(self.central["gameplayEvidence"]["missingGameplayEvents"]),14)
  self.assertEqual(len(self.central["gameplayEvidence"]["existingLaterEventChecks"]),40)
  extra=[x for group in self.central["observations"] for x in group.get("extraUndatedEvidence",[])]
  dated_representation=sum("representation" in row.get("eventKinds",[]) for src in self.data.values() for day,row in src.items() if DATE.fullmatch(day) and day!=RELEASE)
  self.assertEqual(dated_representation,10)
  for cid,tid in (("GIL_188a",791),("GIL_188b",190)):
   self.assertIn("2026-07-22",[x["from"] for x in self.data[cid]["history"]])
   event=self.data[cid]["2026-07-22"]
   self.assertEqual(event["rawTagDelta"][0]["operation"],"roleTransfer")
   self.assertEqual(event["rawTagDelta"][0]["id"],tid)
   self.assertTrue(any(x["findingId"]=="WITCH-BAL-R005" for group in self.data[cid]["observations"]["research"] for x in group.get("extraUndatedEvidence",[])))
  self.assertTrue(any(x["tagId"]==2 and x["date"] is None for x in self.data["GIL_547"]["observations"]["undatedRawTags"]))
  self.assertTrue(any(x["tagId"]==2831 and x["date"] is None for x in self.data["GIL_663t"]["observations"]["undatedRawTags"]))
  self.assertTrue(any(x["tagId"]==1452 and x["date"] is None for x in self.data["GIL_663"]["observations"]["undatedRawTags"]))
 def test_current_line_breaks_and_reference_compatibility(self):
  self.assertEqual(sum("<br></br>" in x.get("text","") for x in self.catalog),81)
  self.assertEqual(sum(len(x.get("referencedTags",[])) for x in self.render),25)
  self.assertEqual(sum(bool(x.get("referencedTags")) for x in self.render),20)
  self.assertEqual(len(self.event_evidence["missingGameplayEvents"]),14)
if __name__=="__main__": unittest.main(verbosity=2)
