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
    self.assertEqual(restored["nativeTags"],revision["changes"]["nativeTags"],cid+":"+revision["from"]+":owned")
    self.assertEqual(restored["referencedTags"],revision["changes"]["referencedTags"],cid+":"+revision["from"]+":referenced")
    for field,value in revision["changes"].items(): self.assertEqual(restored[field],value,cid+":"+revision["from"]+":"+field)
 def test_81_display_breaks_and_current_data_unchanged(self):
  count=sum("<br></br>" in x.get("text","") for x in self.cards)
  self.assertEqual(count,81)
  for c in self.cards:
   self.assertNotIn("\\n",c.get("text","")); self.assertNotIn("/n",c.get("text",""))
 def test_no_editorial_or_undated_observation_promoted(self):
  for src in self.data.values():
   for obs in src["observations"]["undated"].values(): self.assertIsNone(obs["date"])
   self.assertNotIn("flavor",src["patches"][0]["changes"] if src["patches"] else {})
if __name__=="__main__": unittest.main(verbosity=2)
