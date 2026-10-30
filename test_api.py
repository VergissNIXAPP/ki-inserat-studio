"""Offline-API-Test ohne Kontozugriffe, echte Schlüssel oder externe Aufrufe."""
import os,tempfile,unittest,json
from unittest.mock import patch
TMP=tempfile.TemporaryDirectory()
os.environ.update(APP_DATA=TMP.name,APP_PIN='test-pin-not-real-'+'x'*32,OPENAI_API_KEY='test-not-real',ENABLE_KLEINANZEIGEN_ACCESS='false',ENABLE_MARKET_CHECK='false')
from fastapi.testclient import TestClient
import server
class Response:
 status_code=200
 def json(self):return {'choices':[{'message':{'content':json.dumps({'title':'Lampe','description':'Eine Lampe','questions':'Funktion prüfen','price_eur':12})}}]}
class FakeAI:
 async def __aenter__(self):return self
 async def __aexit__(self,*a):pass
 async def post(self,url,**kwargs):
  assert url=='https://api.openai.com/v1/chat/completions'
  return Response()
 async def get(self,*a,**kw):raise AssertionError('Kein Preisabruf erlaubt')
class Tests(unittest.TestCase):
 def setUp(self):self.c=TestClient(server.app);self.h={'X-App-Pin':os.environ['APP_PIN']}
 def test_access(self):
  self.assertEqual(self.c.get('/api/config').status_code,401)
  self.assertEqual(self.c.get('/api/config',headers=self.h).json()['automation_enabled'],False)
  self.assertEqual(self.c.post('/api/analyze',files={'files':('x.jpg',b'fake','image/jpeg')}).status_code,401)
 def test_disabled_account_and_publish(self):
  self.assertEqual(self.c.post('/api/account',headers=self.h,data={'email':'test@example.invalid','password':'fake'}).status_code,409)
  self.assertEqual(self.c.post('/api/publish',headers=self.h,files={'files':('x.jpg',b'fake','image/jpeg')},data={'payload':'{}'}).status_code,409)
 def test_analysis_without_platform_access(self):
  with patch.object(server.httpx,'AsyncClient',return_value=FakeAI()):
   r=self.c.post('/api/analyze',headers=self.h,files={'files':('x.jpg',b'fake','image/jpeg')})
  self.assertEqual(r.status_code,200,r.text)
  self.assertEqual(r.json()['questions'],['Funktion prüfen'])
  self.assertIsNone(r.json()['market']['source_url'])
if __name__=='__main__':unittest.main()
