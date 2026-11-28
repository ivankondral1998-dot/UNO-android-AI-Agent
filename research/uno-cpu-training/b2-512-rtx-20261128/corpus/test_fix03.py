import json, tempfile, pathlib, unittest
from unittest.mock import patch
import prepare_uno as p

class Fix03(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.st=p.Store(self.root)
 def tearDown(self):self.st.db.close();self.tmp.cleanup()
 def test_cross_holdout(self):
  self.st.chat([('user','Как открыть настройки?'),('assistant','Откройте меню.')],'validation','a',{})
  self.st.chat([('user','Как открыть настройки!'),('assistant','Нажмите значок.')],'test','b',{})
  c,n=self.st.finish(self.root);self.assertEqual(n,1);self.assertEqual(c,{'dialogue/test/b':1})
 def test_prior_train_not_new_holdout(self):
  self.st.chat([('user','Как открыть настройки?'),('assistant','Откройте меню.')],'train','r54:old',{})
  self.st.chat([('user','Как открыть настройки!'),('assistant','Нажмите значок.')],'test','b',{})
  c,n=self.st.finish(self.root);self.assertEqual(n,1);self.assertEqual(c,{'dialogue/train/r54:old':1})
 def test_conflicting_intent(self):
  for intent in ['alarm_set','alarm_remove']:self.st.intent('Поставь будильник','train','massive',{},intent,[])
  c,n=self.st.finish(self.root);self.assertEqual(n,2);self.assertFalse(c)
 def test_quality_align(self):
  j=dict(language_identification=['target','target'],intent_score=[1,1],slots_score=[1,1],grammar_score=[4,4],spelling_score=[2,2])
  r=dict(id='1',utt='Поставь таймер на пять минут',intent='alarm_set',annot_utt='Поставь таймер на [time: пять минут]',locale='ru-RU',partition='train',judgments=j)
  bad=[dict(r,judgments={}),dict(r,annot_utt='Поставь таймер на [time: шесть минут]'),dict(r,intent='iot_coffee'),dict(r,annot_utt='Поставь таймер на [person: пять минут]')]
  with patch.object(p,'parquet_rows',return_value=iter([r,*bad])):p.massive(self.st,self.root/'massive-train.parquet')
  self.assertEqual(self.st.i,1);self.assertEqual(sum(self.st.count.values()),4)
 def test_special_casefold_and_format(self):
  self.assertFalse(p.clean('Привет <ASSISTANT>'));self.assertFalse(p.clean('прив\u202eет'))
 def test_everyday_prose_only(self):
  p.base_import(self.st,p.HERE/'UNO_R54_RU_DATA_EXPANDED_20261128.zip',self.root)
  c=self.st.db.execute("SELECT kind,count(*) FROM records WHERE source=? GROUP BY kind",('r54:'+p.EVERYDAY,)).fetchall();self.assertEqual(c,[('language',20)])
 def test_non_alternation_and_english(self):
  self.st.chat([('user','Привет'),('user','Давай'),('assistant','Ответ')],'train','x',{})
  self.st.chat([('user','Привет'),('assistant','Hello everyone')],'train','x',{})
  self.assertEqual(self.st.i,0)
if __name__=='__main__':unittest.main()
