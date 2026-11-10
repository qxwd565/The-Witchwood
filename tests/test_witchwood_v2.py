import copy, json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p): return json.loads(p.read_text(encoding="utf-8"))
class WitchwoodV2Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.cards=read(ROOT/"cards.json")["cards"]
  cls.render=read(ROOT/"render.json")["cards"]
  cls.history=read(ROOT/"history.json")["cards"]
  cls.central=read(ROOT/"sources/baseline/data-history.json")["events"]
  cls.baseline={x["id"]:x for x in read(ROOT/"sources/baseline/cards.json")["cards"]}
  cls.data={p.stem:read(p) for p in (ROOT/"data").glob("GIL_*.json")}
 @staticmethod
 def valmap(rows): return {x["id"]:x.get("value") for x in rows}
 def test_156_card_set_and_metadata(self):
  self.assertEqual(len(self.cards),156); self.assertEqual(len(self.render),156); self.assertEqual(len(self.data),156)
  self.assertEqual(sum(bool(x.get("collectible")) for x in self.cards),135)
  self.assertEqual(sum(not bool(x.get("collectible")) for x in self.cards),21)
  for cid,src in self.data.items():
   base=next(x for x in self.baseline.values() if x["id"]==cid)
   self.assertEqual(src["mode"],read(ROOT/"sources/baseline/cards-data"/(cid+".json"))["mode"])
   self.assertEqual(src["artworkProvenance"],read(ROOT/"sources/baseline/cards-data"/(cid+".json"))["artworkProvenance"])
   self.assertEqual(src["card"]["portrait"],base.get("portrait"))
   self.assertEqual(src["card"]["art"],base.get("art"))
   self.assertEqual(src["card"]["text"],base.get("text"))
   self.assertEqual(src["current"]["id"],cid)
   self.assertEqual(src["current"]["dbfId"],base["dbfId"])
 def test_current_values_only_approved_tag_addition(self):
  rendered={x["id"]:x for x in self.render}
  for cid,base in self.baseline.items():
   now=rendered[cid]
   for key,value in base.items():
    if key=="nativeTags": continue
    self.assertEqual(now.get(key),value,f"{cid}:{key}")
   expected=self.valmap(base.get("nativeTags",[]))
   actual=self.valmap(now.get("nativeTags",[])+now.get("referencedTags",[]))
   if cid=="GIL_152": expected[227]=1
   self.assertEqual(actual,expected,cid)
  tags=self.valmap(rendered["GIL_152"]["nativeTags"])
  self.assertEqual(tags[227],1)
 def test_undead_dates_and_existing_events(self):
  self.assertEqual(len(self.central["2018-04-13"]),156)
  self.assertEqual(sum(len(v) for d,v in self.central.items() if d!="2018-04-13"),40)
  self.assertEqual(len(self.central["2022-12-07"]),25)
  for cid in ("GIL_117","GIL_198","GIL_207","GIL_510","GIL_513","GIL_515","GIL_526","GIL_545","GIL_553t","GIL_557","GIL_616","GIL_616t","GIL_616t2","GIL_618","GIL_635","GIL_655","GIL_658","GIL_667","GIL_678","GIL_694","GIL_805","GIL_815","GIL_825","GIL_840","GIL_902"):
   src=self.data[cid]
   self.assertTrue(any(x["from"]=="2022-11-30" for x in src["history"]),cid)
   self.assertFalse(any(x["from"]=="2022-12-07" for x in src["history"]),cid)
 def test_launch_state_and_type_fields(self):
  for cid,src in self.data.items():
   initial=src["initialSpec"]; self.assertEqual(src["_meta"]["releasedAt"],"2018-04-13")
   kind=initial["type"]
   if kind=="MINION":
    for f in ("armor","durability","spellSchool"): self.assertNotIn(f,initial,cid+":"+f)
   if kind=="SPELL":
    for f in ("armor","attack","durability","health","race","races"): self.assertNotIn(f,initial,cid+":"+f)
   if kind=="HERO": self.assertNotIn("health",initial,cid)
   self.assertIn("nativeTags",initial); self.assertIn("referencedTags",initial)
 def test_all_11_launch_cards_and_13_initial_fields(self):
  specs={cid:src["initialSpec"] for cid,src in self.data.items()}
  self.assertEqual(specs["GIL_191"]["cost"],4)
  self.assertEqual(specs["GIL_531"]["cost"],1)
  self.assertEqual(specs["GIL_547"]["health"],4)
  self.assertEqual(specs["GIL_584"]["races"],[])
  self.assertEqual(specs["GIL_598"]["cost"],8)
  self.assertEqual(specs["GIL_653"]["text"],"<b>죽음의 메아리:</b><br></br>무작위 아군 <b>속공</b> 하수인 하나에게 +2/+1을 부여합니다.")
  self.assertEqual(specs["GIL_663"]["cost"],2)
  self.assertEqual(specs["GIL_663"]["text"],"2/2 나무정령 셋을 내 손으로 가져옵니다.")
  self.assertEqual(specs["GIL_663t"]["cost"],2)
  self.assertEqual(specs["GIL_667"]["health"],5)
  self.assertEqual(specs["GIL_667"]["text"],"<b>도발</b>, <b>죽음의 메아리:</b><br></br>내 영웅의 생명력을<br></br>4 회복시킵니다.")
  self.assertEqual(specs["GIL_801"]["cost"],2)
  self.assertEqual(specs["GIL_836"]["text"],"<b>전투의 함성</b> 하수인을<br></br>하나 <b>발견</b>합니다.")
  self.assertIn("[x]",specs["GIL_667"]["nativeRawText"])
  self.assertIn("\n",specs["GIL_653"]["nativeRawText"])
  hagatha=self.data["GIL_504"]["initialSpec"]
  self.assertEqual(hagatha["armor"],5)
  self.assertEqual(next(x["value"] for x in hagatha["nativeTags"] if x["id"]==45),30)
  hero_power=self.data["GIL_504h"]["initialSpec"]
  self.assertEqual(hero_power["cost"],0)
  self.assertIs(hero_power["collectible"],False)
  empty=self.data["GIL_616t2"]["current"]
  self.assertEqual(empty["text"],"")
  current_string=self.data["GIL_616t2"]["_meta"]["currentStrings"].get("184",{}).get("locales",{}).get("koKR")
  if current_string is not None:
   self.assertTrue(current_string["present"])
   self.assertEqual(current_string["nativeRawText"],"")
  self.assertEqual(sum(len(x.get("referencedTags",[])) for x in self.render),25)
  self.assertEqual(sum(bool(x.get("referencedTags")) for x in self.render),20)
 def test_confirmed_missing_patch_events(self):
  count=0
  for cid,src in self.data.items():
   dates={p["date"] for p in src["patches"]}
   for expected in {
    "GIL_584":["2018-07-11"],"GIL_545":["2018-08-03"],"GIL_801":["2021-03-26"],
    "GIL_191":["2021-05-13"],"GIL_547":["2022-04-06"],"GIL_598":["2022-05-20"],
    "GIL_653":["2023-04-05"],"GIL_663":["2023-04-05"],"GIL_663t":["2023-04-05"],
    "GIL_667":["2023-05-20"],"GIL_531":["2026-04-15"],"GIL_836":["2025-03-19","2026-07-22","2026-08-19"]
   }.get(cid,[]):
    self.assertIn(expected,dates,cid); count+=1
  self.assertEqual(count,14)
 def test_historical_raw_tag_corrections(self):
  for cid,day,tag_id,value in (("GIL_191","2021-03-26",48,4),("GIL_663","2021-03-26",48,2),("GIL_667","2022-11-30",45,5)):
   rev=next(x for x in self.data[cid]["history"] if x["from"]==day)
   tag=next(x for x in rev["changes"]["nativeTags"] if x["id"]==tag_id)
   self.assertEqual(tag["value"],value)
 def test_legacy_replay_restores_every_date_and_tag_role(self):
  rendered={x["id"]:x for x in self.render}
  for cid,src in self.data.items():
   card=rendered[cid]
   dbf=str(card["dbfId"])
   legacy=self.history[dbf]
   self.assertEqual(legacy["id"],cid)
   self.assertEqual(legacy["initialSpec"],src["initialSpec"])
   self.assertEqual(legacy["patches"],src["patches"])
   self.assertEqual(src["history"][0]["from"],"2018-04-13")
   for revision in src["history"]:
    restored=copy.deepcopy(card)
    restored.update(copy.deepcopy(revision["changes"]))
    for field in revision.get("removedFields",[]): restored.pop(field,None)
    self.assertEqual(restored["nativeTags"],revision["changes"].get("nativeTags",card["nativeTags"]),cid+":"+revision["from"]+":owned")
    self.assertEqual(restored["referencedTags"],revision["changes"].get("referencedTags",card.get("referencedTags",[])),cid+":"+revision["from"]+":referenced")
    for field,value in revision["changes"].items(): self.assertEqual(restored[field],value,cid+":"+revision["from"]+":"+field)
 def test_81_display_breaks_and_current_data_unchanged(self):
  count=sum("<br></br>" in x.get("text","") for x in self.cards)
  self.assertEqual(count,81)
  for c in self.cards:
   self.assertNotIn("\\n",c.get("text","")); self.assertNotIn("/n",c.get("text",""))
 def test_date_first_canonical_source_and_sparse_tag_deltas(self):
  source=read(ROOT/"sources/witchwood-history-v2.json")
  self.assertEqual(source["format"],"date-first-delta")
  self.assertEqual(len(source["events"]["2018-04-13"]),156)
  self.assertEqual(sum(len(v) for d,v in source["events"].items() if d!="2018-04-13"),53)
  self.assertEqual(len(source["events"]["2022-11-30"]),25)
  self.assertNotIn("2022-12-07",source["events"])
  for cid in ("GIL_557","GIL_678","GIL_902"):
   event=source["events"]["2022-11-30"][cid]
   self.assertNotIn("nativeTags",event["changes"])
  for cid,src in self.data.items():
   state=copy.deepcopy(source["events"]["2018-04-13"][cid])
   for day in sorted(d for d in source["events"] if d!="2018-04-13"):
    entry=source["events"][day].get(cid)
    if not entry: continue
    state.update(copy.deepcopy(entry.get("changes",{})))
    for field in entry.get("removedFields",[]): state.pop(field,None)
   self.assertEqual(state["id"],cid)
   self.assertEqual(state["dbfId"],src["current"]["dbfId"])
 def test_research_observations_are_separate_from_gameplay_events(self):
  research=read(ROOT/"sources/witchwood-research-v1.json")
  public=read(ROOT/"sources/witchwood-history-v2.json")
  self.assertEqual(len(research["observations"]),13)
  self.assertEqual(public["observations"],research["observations"])
  self.assertEqual(public["relationships"],research["relationships"])
  self.assertEqual(public["editorial"],research["editorial"])
  self.assertEqual(research["relationships"]["existingEdges"]["count"],15)
  self.assertEqual(len(research["relationships"]["unresolved"]),7)
  for cid,src in self.data.items():
   expected={x["id"] for x in research["observations"] if cid in x.get("cardIds",[])}
   actual={x["id"] for x in src["observations"]["research"]}
   self.assertEqual(actual,expected,cid)
   self.assertNotIn("research",src["patches"][0]["changes"] if src["patches"] else {})
 def test_no_editorial_or_undated_observation_promoted(self):
  for src in self.data.values():
   for obs in src["observations"]["undated"].values(): self.assertIsNone(obs["date"])
   self.assertNotIn("flavor",src["patches"][0]["changes"] if src["patches"] else {})
if __name__=="__main__": unittest.main(verbosity=2)
