import json, hashlib, tempfile, unittest, zipfile, gzip, pathlib, collections
from unittest.mock import patch
import prepare_uno as p

class Regression(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.st=p.Store(self.root)
 def tearDown(self):self.st.db.close();self.tmp.cleanup()
 def test_aya_actual_annotation(self):
  row={'inputs':'Привет, как дела?','targets':'Спасибо, всё хорошо.','language_code':'rus','annotation_type':'original-annotations','user_id':'source-contributor'}
  with patch.object(p,'parquet_rows',return_value=iter([row,dict(row,inputs='Что нового?',annotation_type='re-annotations')])):p.aya(self.st,self.root/'aya.parquet')
  self.assertEqual(self.st.i,1);self.assertNotIn('source-contributor',self.st.db.execute('select payload from records').fetchone()[0])
 def test_aya_group(self):
  items=[{'inputs':f'Как дела {i}?','targets':'Всё хорошо.','language_code':'rus','annotation_type':'original-annotations','user_id':'same'} for i in range(30)]
  with patch.object(p,'parquet_rows',return_value=iter(items)):p.aya(self.st,self.root/'aya.parquet')
  self.assertEqual(self.st.db.execute('select count(distinct split) from records').fetchone()[0],1)
 def test_legacy(self):
  r=p.legacy_tokenizer(self.root);self.assertEqual(r['sha256'],p.LEGACY_SHA);self.assertFalse(r['checkpoint_resume']);self.assertEqual(r['active_vocab'],514)
 def test_oasst_raw_pii(self):
  q={'lang':'ru','role':'prompter','text':'Как дела?','replies':[{'lang':'ru','role':'assistant','text':'Личные данные пользователя.','rank':0,'labels':[{'name':'pii','value':1.0}]},{'lang':'ru','role':'assistant','text':'Хорошо, спасибо!','rank':1}]}
  f=self.root/'oasst2.trees.jsonl.gz'
  with gzip.open(f,'wt',encoding='utf8') as g:g.write(json.dumps({'prompt':q})+'\n')
  p.oasst(self.st,f,True);self.assertEqual(self.st.i,1);self.assertIn('Хорошо, спасибо!',self.st.db.execute('select payload from records').fetchone()[0])
 def test_oasst_derived(self):
  f=self.root/'oasst2_ru_main_branch.jsonl';f.write_text(json.dumps({'id':'test','messages':[{'role':'user','content':'Привет!'},{'role':'bot','content':'Добрый день!'}]})+'\n',encoding='utf8');p.oasst(self.st,f,False);self.assertEqual(self.st.i,1)
 def test_old_test_prompt(self):
  self.st.lock(p.prompt_key('Привет, как дела?'));self.st.chat([('user','ПРИВЕТ как дела!'),('assistant','Нормально.')],'train','x',{});counts,n=self.st.finish(self.root);self.assertEqual(n,1);self.assertEqual(sum(counts.values()),0)
 def test_unmapped_massive(self):
  row={'id':'1','utt':'Включи музыку','intent':12,'annot_utt':'Включи музыку','locale':'ru-RU'}
  with patch.object(p,'parquet_rows',return_value=iter([row])):
   with self.assertRaisesRegex(ValueError,'unresolved'):p.massive(self.st,self.root/'massive-train.parquet')
 def test_base_manifest_and_dialogues(self):
  p.base_import(self.st,p.HERE/'UNO_R54_RU_DATA_EXPANDED_20261128.zip',self.root)
  genres=collections.Counter(json.loads(x[0])['meta'].get('genre') for x in self.st.db.execute("select payload from records where source='r54:literature' and split='train'"))
  self.assertEqual(genres['dialogues'],363);self.assertEqual(genres['language'],779)
  self.assertTrue((self.root/'r54_original'/'language'/'test.jsonl').is_file());self.assertTrue((self.root/'r54_original'/'tools'/'check.py').is_file())
 def test_base_extra_file(self):
  target=self.root/'tampered.zip';target.write_bytes((p.HERE/'UNO_R54_RU_DATA_EXPANDED_20261128.zip').read_bytes());
  with zipfile.ZipFile(target,'a') as z:z.writestr('extra.txt','x')
  with self.assertRaisesRegex(ValueError,'pinned original'):p.base_import(self.st,target,self.root)
  with patch.object(p,'BASE_SHA',p.sha(target)):
   with self.assertRaisesRegex(ValueError,'coverage'):p.base_import(self.st,target,self.root)
 def test_reviewed_pd_hash(self):
  f=self.root/'export';f.mkdir();(f/'manifest.json').write_text(json.dumps({'version':'1.0.0','files':{'train.jsonl':'0'*64}}));(f/'train.jsonl').write_text('abc')
  with self.assertRaisesRegex(ValueError,'checksum'):p.reviewed_pd(self.st,f,self.root)

if __name__=='__main__':unittest.main()
