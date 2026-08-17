from __future__ import annotations
import io,json,tempfile,unittest
from pathlib import Path
from reportlab.pdfgen import canvas
from bassetti_poc.exporter import ApprovalError,assert_exportable,export_docx
from bassetti_poc.extractor import InputError,parse_document,validate_upload
from bassetti_poc.schema import REQUIRED_FIELDS
from bassetti_poc.storage import SessionStore

ROOT=Path(__file__).resolve().parents[1]

class ParserTests(unittest.TestCase):
 def test_all_gold_fixtures(self):
  from scripts.validate_fixtures import compare
  for gold_path in (ROOT/'fixtures/gold').glob('*.json'):
   result=parse_document(gold_path.stem+'.pdf',(ROOT/'samples'/(gold_path.stem+'.pdf')).read_bytes())
   self.assertTrue(all(compare(result,json.loads(gold_path.read_text())).values()),gold_path.name)
 def test_fluent_never_implies_cefr(self):
  result=parse_document('normal_single_column.pdf',(ROOT/'samples/normal_single_column.pdf').read_bytes())
  english=next(x for x in result['fields']['languages']['value'] if x['language']=='English')
  self.assertEqual(english,{'language':'English','original_level':'Fluent','cefr':'Not specified'})
 def test_ambiguity_overlap_sensitive_and_missing_icon_text(self):
  result=parse_document('mixed_fr_en_ambiguous.pdf',(ROOT/'samples/mixed_fr_en_ambiguous.pdf').read_bytes())
  self.assertIn('Ambiguous numeric date',result['fields']['work_experience']['ambiguity'])
  self.assertIn('overlapping',result['fields']['work_experience']['ambiguity'])
  self.assertIsNone(result['fields']['contact.phone']['value'])
  self.assertTrue(any(w['type']=='sensitive_information' for w in result['warnings']))
 def test_invalid_and_unreadable_inputs(self):
  with self.assertRaises(InputError):validate_upload('evil.exe',b'MZ')
  buf=io.BytesIO();c=canvas.Canvas(buf);c.showPage();c.save()
  with self.assertRaisesRegex(InputError,'No readable text'):parse_document('blank.pdf',buf.getvalue())

class WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=SessionStore(Path(self.tmp.name));result=parse_document('normal_single_column.pdf',(ROOT/'samples/normal_single_column.pdf').read_bytes());self.session=self.store.create(result)
 def tearDown(self):self.tmp.cleanup()
 def test_audit_and_export_gate(self):
  with self.assertRaises(ApprovalError):assert_exportable(self.session)
  s=self.store.update_field(self.session['id'],'contact.name','Maya L.','save');self.assertEqual(s['audit'][0]['old_value'],'Maya Laurent');self.assertEqual(s['audit'][0]['new_value'],'Maya L.')
  for field in REQUIRED_FIELDS:s=self.store.update_field(self.session['id'],field,s['result']['fields'][field]['value'],'confirm')
  assert_exportable(s);data=export_docx(s);self.assertTrue(data.startswith(b'PK'));self.assertGreater(len(data),10000)
 def test_follow_up_blocks_and_reset_preserves_audit(self):
  s=self.store.update_field(self.session['id'],'contact.phone',self.session['result']['fields']['contact.phone']['value'],'follow_up');self.assertEqual(s['result']['fields']['contact.phone']['review_status'],'follow_up')
  s=self.store.reset_review(self.session['id']);self.assertTrue(all(f['review_status']=='unreviewed' for f in s['result']['fields'].values()));self.assertGreaterEqual(len(s['audit']),2)

if __name__=='__main__':unittest.main()

