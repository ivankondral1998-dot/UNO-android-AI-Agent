import unittest, tempfile, pathlib, json, gzip, bz2
from unittest.mock import patch
import prepare_uno as p
class Test(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.st=p.Store(self.root)
 def tearDown(self):self.st.db.close();self.tmp.cleanup()
 def test_holdout_priority(self):
  self.st.chat([('user','Как включить свет?'),('assistant','Ответ один.')],'train','a',{})
  self.st.chat([('user','КАК  включить свет?'),('assistant','Ответ другой.')],'test','b',{})
  self.st.lang('Текст для обучения.','train','c',{})
  self.st.lang('Текст для обучения.','train','d',{})
  c,n=self.st.finish(self.root);self.assertEqual(n,2);self.assertEqual(sum(c.values()),2)
 def test_aya_filter(self):
  data=[dict(inputs='Как дела?',targets='Хорошо.',language_code='rus',annotation_type='original_annotations'),dict(inputs='Что нового?',targets='Ничего.',language_code='rus',annotation_type='re-annotations'),dict(inputs='Hello?',targets='Hello.',language_code='eng',annotation_type='original_annotations')]
  with patch.object(p,'parquet_rows',return_value=iter(data)):p.aya(self.st,self.root/'aya.parquet')
  self.assertEqual(self.st.i,1)
 def test_massive(self):
  data=[dict(id='1',utt='Поставь таймер на пять минут',intent='alarm_set',annot_utt='Поставь таймер на [time: пять минут]',locale='ru-RU',partition='train',judgments=[dict(language_identification='target',intent_score=1,slots_score=1,grammar_score=4,spelling_score=2)]*2)]
  with patch.object(p,'parquet_rows',return_value=iter(data)):p.massive(self.st,self.root/'massive-train.parquet')
  r=json.loads(self.st.db.execute('SELECT payload FROM records').fetchone()[0]);self.assertEqual(r['slots'],[{'name':'time','value':'пять минут'}])
 def test_pd(self):
  data=[dict(text='Русский текст для проверки. '*1000,identifier='1',creator='Автор',title='Книга',publication_date=1800)]
  with patch.object(p,'parquet_rows',return_value=iter(data)):p.pd(self.st,self.root/'russian_pd_1.parquet',8000)
  self.assertGreater(self.st.i,0);self.assertEqual(self.st.db.execute('SELECT COUNT(DISTINCT split) FROM records').fetchone()[0],1)
 def test_pii(self):
  self.assertFalse(p.clean('Почта user@example.org'));self.assertFalse(p.clean('Телефон +7 (900) 123-45-67'));self.assertTrue(p.clean('Время 12:30'))
 def test_no_special_injection(self):self.assertFalse(p.clean('Привет <assistant>'))
if __name__=='__main__':unittest.main()
