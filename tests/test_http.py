from __future__ import annotations
import json,threading,unittest,urllib.error,urllib.request
from bassetti_poc.app import AppHandler
from bassetti_poc.schema import REQUIRED_FIELDS
from http.server import ThreadingHTTPServer

class HttpFlowTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=ThreadingHTTPServer(('127.0.0.1',0),AppHandler);cls.port=cls.server.server_address[1];cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
 def request(self,path,method='GET',payload=None):
  data=json.dumps(payload).encode() if payload is not None else None;headers={'Content-Type':'application/json'} if data else {};req=urllib.request.Request(f'http://127.0.0.1:{self.port}{path}',data=data,headers=headers,method=method);return urllib.request.urlopen(req,timeout=5)
 def test_complete_sample_review_export_and_reset(self):
  root=self.request('/');self.assertIn(b'Evidence first',root.read());self.assertEqual(root.headers['X-Frame-Options'],'DENY')
  session=json.load(self.request('/api/parse','POST',{'sample_id':'mixed_fr_en_ambiguous'}));sid=session['id']
  self.assertIsNone(session['result']['fields']['contact.phone']['value'])
  with self.assertRaises(urllib.error.HTTPError) as ctx:self.request(f'/api/sessions/{sid}/export/json')
  self.assertEqual(ctx.exception.code,409);self.assertIsNone(json.load(self.request(f'/api/sessions/{sid}'))['approved_at'])
  for field in REQUIRED_FIELDS:
   value=session['result']['fields'][field]['value'];session=json.load(self.request(f'/api/sessions/{sid}/fields','POST',{'field':field,'value':value,'action':'confirm'}))
  exported=self.request(f'/api/sessions/{sid}/export/json');payload=json.load(exported);self.assertEqual(payload['review']['status'],'human_approved');self.assertEqual(payload['languages'][1]['cefr'],'Not specified')
  docx=self.request(f'/api/sessions/{sid}/export/docx').read();self.assertTrue(docx.startswith(b'PK'))
  reset=json.load(self.request(f'/api/sessions/{sid}/reset-review','POST',{}));self.assertTrue(all(x['review_status']=='unreviewed' for x in reset['result']['fields'].values()));self.assertIsNone(reset['approved_at'])

if __name__=='__main__':unittest.main()
