import base64, copy, gzip, json, re, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RELEASE="2018-04-13"
DATE=re.compile(r"^\d{4}-\d{2}-\d{2}$")
def read(p): return json.loads(p.read_text(encoding="utf-8"))
class WitchwoodV2Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.cards=read(ROOT/"cards.json")["cards"]
  cls.render=read(ROOT/"render.json")["cards"]
  cls.legacy=read(ROOT/"history.json")["cards"]
  cls.central=read(ROOT/"sources/baseline/data-history.json")["events"]
  cls.public=read(ROOT/"data/history.json")
  cls.research=read(ROOT/"sources/witchwood-research-v1.json")
  cls.manifest=read(ROOT/"sources/witchwood-source-manifest.json")
  cls.baseline={x["id"]:x for x in read(ROOT/"sources/baseline/cards.json")["cards"]}
  cls.data={p.stem:read(p) for p in (ROOT/"data").glob("GIL_*.json")}
  cls.rendered={x["id"]:x for x in cls.render}
 @staticmethod
 def valmap(rows): return {x["id"]:x.get("value") for x in rows}
 def test_156_card_set_and_metadata(self):
  self.assertEqual(len(self.cards),156); self.assertEqual(len(self.render),156); self.assertEqual(len(self.data),156)
  self.assertEqual(len(self.legacy),156)
  self.assertEqual(sum(bool(x.get("collectible")) for x in self.cards),135)
  self.assertEqual(sum(not bool(x.get("collectible")) for x in self.cards),21)
  for cid,src in self.data.items():
   base=self.baseline[cid]
   source_base=read(ROOT/"sources/baseline/cards-data"/(cid+".json"))
   self.assertEqual(src["mode"],source_base["mode"])
   self.assertEqual(src["artworkProvenance"],source_base["artworkProvenance"])
   self.assertEqual(src["card"]["portrait"],base.get("portrait"))
   self.assertEqual(src["card"]["art"],base.get("art"))
   self.assertEqual(src["current"]["id"],cid)
   self.assertEqual(src["current"]["dbfId"],base["dbfId"])
   self.assertEqual(src["_meta"]["current"],src["current"])
   self.assertEqual(src["_meta"]["mode"],src["mode"])
   self.assertEqual(src["_meta"]["artworkProvenance"],src["artworkProvenance"])
   self.assertEqual(src["_meta"]["portrait"],base.get("portrait"))
   self.assertEqual(src["_meta"]["art"],base.get("art"))
 def test_current_legacy_flat_tags_match_immutable_baseline(self):
  refs=ref_cards=0
  for cid,base in self.baseline.items():
   expected=copy.deepcopy(base.get("nativeTags",[]))
   if cid=="GIL_152" and not any(x.get("id")==227 for x in expected):
    expected.append({"id":227,"name":"공격 불가","value":1})
   expected.sort(key=lambda x:x["id"])
   actual=copy.deepcopy(self.rendered[cid].get("nativeTags",[])); actual.sort(key=lambda x:x["id"])
   self.assertEqual(actual,expected,cid)
   refs+=len(self.rendered[cid].get("referencedTags",[]))
   ref_cards+=bool(self.rendered[cid].get("referencedTags"))
  self.assertEqual(refs,25); self.assertEqual(ref_cards,20)
  self.assertEqual(self.valmap(self.rendered["GIL_152"]["nativeTags"])[227],1)
 def test_actual_top_level_dates_and_legacy_shapes(self):
  self.assertEqual(self.public["format"],"date-first-delta")
  self.assertEqual(self.public,read(ROOT/"sources/witchwood-history-v2.json"))
  self.assertEqual(len(self.public["events"][RELEASE]),156)
  self.assertEqual(sum(len(v) for d,v in self.public["events"].items() if d!=RELEASE),63)
  for cid,src in self.data.items():
   days=sorted(k for k in src if DATE.fullmatch(k))
   self.assertEqual(days[0],RELEASE,cid)
   self.assertEqual(days,sorted(x["from"] for x in src["history"]),cid)
   self.assertEqual(src[RELEASE]["type"],src["initialSpec"]["type"],cid)
   for field,value in src["initialSpec"].items():
    self.assertEqual(src[RELEASE].get(field),value,(cid,field))
   self.assertEqual(self.legacy[str(src["current"]["dbfId"])]["initialSpec"],src["initialSpec"])
   self.assertEqual(self.legacy[str(src["current"]["dbfId"])]["patches"],src["patches"])
   self.assertEqual(self.rendered[cid]["history"],src["history"])
 def test_launch_values_and_zero_presence_semantics(self):
  specs={cid:src["initialSpec"] for cid,src in self.data.items()}
  self.assertEqual(specs["GIL_191"]["cost"],4)
  self.assertEqual(specs["GIL_531"]["cost"],1)
  self.assertEqual(specs["GIL_547"]["health"],4)
  self.assertEqual(specs["GIL_584"]["races"],[])
  self.assertEqual(specs["GIL_598"]["cost"],8)
  self.assertEqual(specs["GIL_663"]["cost"],2)
  self.assertEqual(specs["GIL_663"]["text"],"2/2 나무정령 셋을 내 손으로 가져옵니다.")
  self.assertEqual(specs["GIL_663t"]["cost"],2)
  self.assertEqual(specs["GIL_667"]["health"],5)
  self.assertEqual(specs["GIL_801"]["cost"],2)
  self.assertEqual(specs["GIL_504"]["health"],30)
  self.assertEqual(specs["GIL_504"]["armor"],5)
  self.assertEqual(specs["GIL_504h"]["cost"],0)
  self.assertIs(specs["GIL_504h"]["collectible"],False)
  self.assertEqual(specs["GIL_600"]["cost"],0)
  self.assertEqual(specs["GIL_616t2"]["text"],"")
  self.assertEqual(specs["GIL_681"]["race"],"모든 종족")
  self.assertEqual(specs["GIL_681"]["races"],["ALL"])
  for cid in ("GIL_188a","GIL_188b"):
   self.assertEqual(specs[cid]["type"],"SPELL")
   for field in ("cost","attack","health"): self.assertNotIn(field,specs[cid],cid+":"+field)
 def test_launch_xml_string_presence_and_raw_text(self):
  for cid,src in self.data.items():
   strings=src["_meta"]["launchStrings"]
   for tid in ("184","185"):
    if tid in strings:
     self.assertTrue(strings[tid]["present"])
     for locale in ("koKR","enUS"):
      self.assertIn(locale,strings[tid]["locales"],(cid,tid,locale))
      self.assertTrue(strings[tid]["locales"][locale]["present"])
  self.assertIn("[x]",self.data["GIL_667"]["initialSpec"]["nativeRawText"])
  self.assertIn("\n",self.data["GIL_667"]["initialSpec"]["nativeRawText"])
  self.assertEqual(self.data["GIL_616t2"]["initialSpec"]["text"],"")
 def test_13_initial_field_corrections(self):
  s={cid:x["initialSpec"] for cid,x in self.data.items()}
  self.assertEqual(s["GIL_653"]["text"],"<b>죽음의 메아리:</b><br></br>무작위 아군 <b>속공</b> 하수인 하나에게 +2/+1을 부여합니다.")
  self.assertEqual(s["GIL_667"]["text"],"<b>도발</b>, <b>죽음의 메아리:</b><br></br>내 영웅의 생명력을<br></br>4 회복시킵니다.")
  self.assertEqual(s["GIL_836"]["text"],"<b>전투의 함성</b> 하수인을<br></br>하나 <b>발견</b>합니다.")
 def test_existing_40_and_13_missing_gameplay_rows(self):
  self.assertEqual(len(self.central[RELEASE]),156)
  self.assertEqual(sum(len(v) for d,v in self.central.items() if d!=RELEASE),40)
  self.assertEqual(len(self.public["events"]["2022-11-30"]),25)
  self.assertNotIn("2022-12-07",self.public["events"])
  for cid in ("GIL_117","GIL_198","GIL_207","GIL_510","GIL_513","GIL_515","GIL_526","GIL_545","GIL_553t","GIL_557","GIL_616","GIL_616t","GIL_616t2","GIL_618","GIL_635","GIL_655","GIL_658","GIL_667","GIL_678","GIL_694","GIL_805","GIL_815","GIL_825","GIL_840","GIL_902"):
   self.assertIn("2022-11-30",{x["from"] for x in self.data[cid]["history"]},cid)
  expected={"GIL_584":"2018-07-11","GIL_545":"2018-08-03","GIL_801":"2021-03-26",
   "GIL_191":"2021-05-13","GIL_547":"2022-04-06","GIL_598":"2022-05-20",
   "GIL_653":"2023-04-05","GIL_663":"2023-04-05","GIL_663t":"2023-04-05",
   "GIL_667":"2023-05-20","GIL_531":"2026-04-15"}
  for cid,day in expected.items(): self.assertIn(day,{x["from"] for x in self.data[cid]["history"]},cid)
  self.assertEqual(self.data["GIL_836"]["patches"][-1]["date"],"2026-08-19")
 def test_historical_raw_corrections_do_not_copy_future_metadata(self):
  for cid,day,tag_id,value in (("GIL_191","2021-03-26",48,4),("GIL_663","2021-03-26",48,2),("GIL_667","2022-11-30",45,5)):
   tags=self.data[cid][day]["nativeTags"]
   self.assertEqual(next(x["value"] for x in tags if x["id"]==tag_id),value)
  for cid in ("GIL_191","GIL_553","GIL_663"):
   self.assertFalse(any(x["id"]==1452 for x in self.data[cid]["2021-03-26"]["nativeTags"]),cid)
  self.assertFalse(any(x["id"]==3881 for x in self.data["GIL_553t"]["2022-11-30"]["nativeTags"]))
  for cid in ("GIL_191","GIL_663","GIL_600"):
   self.assertFalse(any(x["id"]==114 and x.get("value")==0 for x in self.data[cid]["2021-03-26"]["nativeTags"]))
 def test_confirmed_representation_events_are_not_gameplay(self):
  for cid in ("GIL_188a","GIL_188b"):
   self.assertEqual(self.data[cid]["2018-11-30"]["type"],"MINION")
   self.assertIn("representation",self.data[cid]["2018-11-30"])
   self.assertIn("representation",self.data[cid]["2026-07-22"])
   self.assertNotIn("gameplay",self.data[cid]["2026-07-22"]["eventKinds"])
  self.assertEqual(self.data["GIL_681"]["2021-05-13"]["text"],"<i>모든 종족값을 가집니다.</i>")
  for cid in ("GIL_596","GIL_653","GIL_672"):
   snap=self.data[cid]["2025-03-19"]
   self.assertTrue(any(x["id"]==45 for x in snap["nativeTags"]))
   self.assertFalse(any(x["id"]==187 for x in snap["nativeTags"]))
   self.assertEqual(snap["durability"],self.data[cid]["initialSpec"]["durability"])
  for cid in ("GIL_134","GIL_687"):
   self.assertIn("2026-03-11",{x["from"] for x in self.data[cid]["history"]})
 def test_legacy_replay_from_current_restores_every_interval(self):
  for cid,src in self.data.items():
   current=copy.deepcopy(self.rendered[cid])
   self.assertEqual(self.legacy[str(src["current"]["dbfId"])]["initialSpec"],src["initialSpec"])
   for revision in src["history"]:
    restored=copy.deepcopy(current)
    restored.update(copy.deepcopy(revision["changes"]))
    for field in revision.get("removedFields",[]): restored.pop(field,None)
    for field,value in revision["changes"].items():
     self.assertEqual(restored.get(field),value,(cid,revision["from"],field))
    snap=src[revision["from"]]
    for field in ("type","cost","attack","health","collectible","text","nativeRawText","nativeTags","nativeTagOrigins","ownedTags","referencedTags"):
     if field in snap: self.assertEqual(restored.get(field),snap[field],(cid,revision["from"],field))
 def test_current_role_map_keeps_flattened_legacy_tags(self):
  total=cards=0
  for card in self.cards:
   refs=card.get("referencedTags",[])
   total+=len(refs); cards+=bool(refs)
   roles={x["id"]:x["role"] for x in card.get("nativeTagOrigins",[])}
   for row in refs: self.assertEqual(roles[row["id"]],"referenced")
   for row in card["nativeTags"]:
    self.assertIn(roles.get(row["id"]),("owned","referenced","legacy-only"))
  self.assertEqual(total,25); self.assertEqual(cards,20)
 def test_research_observations_and_source_manifest(self):
  self.assertEqual(len(self.research["observations"]),13)
  self.assertEqual(self.manifest["count"],40)
  self.assertEqual(len(self.manifest["entries"]),40)
  self.assertEqual(self.public["sourceManifest"],self.manifest)
  evidence_b64=(ROOT/"sources/witchwood-observations-evidence.json.gz.b64").read_text(encoding="utf-8").splitlines()[-1].strip()
  evidence=json.loads(gzip.decompress(base64.b64decode(evidence_b64)))
  event_b64=(ROOT/"sources/witchwood-event-evidence.json.gz.b64").read_text(encoding="utf-8").splitlines()[-1].strip()
  event_evidence=json.loads(gzip.decompress(base64.b64decode(event_b64)))
  self.assertEqual(len(evidence),13)
  self.assertEqual(len(event_evidence["missingGameplayEvents"]),14)
  self.assertEqual(len(event_evidence["existingLaterEventChecks"]),40)
  self.assertEqual(self.public["gameplayEvidence"],event_evidence)
  self.assertEqual(len(self.public["observations"]),13)
  for summary,raw in zip(self.public["observations"],evidence):
   self.assertEqual(summary["findingId"],raw["findingId"])
   self.assertEqual(summary["cardIds"],raw["ids"])
   self.assertEqual(summary["archiveEvidence"],raw["archiveEvidence"])
  for cid,src in self.data.items():
   expected={x["id"] for x in self.research["observations"] if cid in x.get("cardIds",[])}
   actual={x["id"] for x in src["observations"]["research"]}
   self.assertEqual(actual,expected,cid)
   expected_missing=any(x["id"]==cid for x in event_evidence["missingGameplayEvents"])
   expected_existing=any(x["id"]==cid for x in event_evidence["existingLaterEventChecks"])
   self.assertEqual(bool(src["_meta"]["gameplayEvidence"]["missing"]),expected_missing,cid+":missing evidence")
   self.assertEqual(bool(src["_meta"]["gameplayEvidence"]["existing"]),expected_existing,cid+":existing evidence")
   self.assertNotIn("research",src["patches"][0]["changes"] if src["patches"] else {})
 def test_81_current_line_break_cards_and_raw_text_sync(self):
  self.assertEqual(sum("<br></br>" in x.get("text","") for x in self.cards),81)
  for card in self.cards:
   self.assertNotIn("\\n",card.get("text","")); self.assertNotIn("/n",card.get("text",""))
  for cid in ("GIL_653","GIL_667","GIL_836","GIL_134","GIL_687"):
   src=self.data[cid]
   self.assertEqual(src["current"]["nativeRawText"],src["nativeRawText"])
   self.assertNotEqual(src["current"]["nativeRawText"],"")
 def test_no_editorial_or_undated_observation_promoted(self):
  for src in self.data.values():
   for obs in src["observations"]["undated"].values(): self.assertIsNone(obs["date"])
   self.assertNotIn("flavor",src["patches"][0]["changes"] if src["patches"] else {})
if __name__=="__main__": unittest.main(verbosity=2)
