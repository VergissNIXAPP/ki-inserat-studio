import os,json,base64,hmac,uuid,asyncio,re,statistics
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from fastapi import FastAPI,UploadFile,File,Form,HTTPException,Depends,Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import httpx
from bs4 import BeautifulSoup
from app_utils import normalize_analysis
from fastapi import Request

os.umask(0o077)
ROOT=Path(__file__).parent; DATA=Path(os.getenv('APP_DATA',str(ROOT/'data'))); DATA.mkdir(parents=True,exist_ok=True)
load_dotenv(ROOT/'.env')
# Zugang bleibt im Cloudbetrieb verpflichtend.
if len(os.getenv('APP_PIN','')) < 24: raise RuntimeError('APP_PIN muss mindestens 24 Zeichen lang sein. python3 setup.py ausführen.')
app=FastAPI(title='KI Inserat Studio Pro');app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
JOBS={};ACTIVE=asyncio.Lock()
@app.get('/')
def index():return FileResponse(ROOT/'static'/'index.html')
@app.get('/api/health')
def health():return {'ok':True}
def auth(x_app_pin:str=Header(default='')):
    pin=os.getenv('APP_PIN','')
    if len(pin)<24 or pin=='change-me-to-a-long-secret-pin':raise HTTPException(503,'APP_PIN muss mindestens 24 Zeichen lang sein')
    if not hmac.compare_digest(x_app_pin,pin):raise HTTPException(401,'App-PIN falsch')
def cipher():
    key=os.getenv('CREDENTIAL_KEY','')
    if not key:raise HTTPException(503,'CREDENTIAL_KEY in .env fehlt')
    try:return Fernet(key.encode())
    except Exception:raise HTTPException(503,'CREDENTIAL_KEY ungültig')
@app.post('/api/account')
async def account(email:str=Form(...),password:str=Form(...),_=Depends(auth)):
    if os.getenv('ENABLE_KLEINANZEIGEN_ACCESS','false').lower()!='true':raise HTTPException(409,'Kleinanzeigen-Zugriff deaktiviert. Für Fotoanalyse sind keine Kleinanzeigen-Zugangsdaten nötig.')
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$',email) or not password:raise HTTPException(400,'E-Mail oder Passwort ungültig')
    (DATA/'account.enc').write_bytes(cipher().encrypt(json.dumps({'email':email,'password':password}).encode()))
    os.chmod(DATA/'account.enc',0o600)
    return {'saved':True,'note':'Zugangsdaten verschlüsselt auf Raspberry Pi gespeichert, Anmeldung noch nicht getestet'}
@app.delete('/api/account')
async def remove_account(_=Depends(auth)):
    (DATA/'account.enc').unlink(missing_ok=True)
    return {'deleted':True}
@app.post('/api/analyze')
async def analyze(files:list[UploadFile]=File(...),notes:str=Form(''),_=Depends(auth)):
    key=os.getenv('OPENAI_API_KEY')
    if not key:raise HTTPException(503,'OPENAI_API_KEY fehlt')
    if not 1<=len(files)<=8:raise HTTPException(400,'1–8 Bilder notwendig')
    images=[]
    for f in files:
        if f.content_type not in ('image/jpeg','image/png','image/webp'):raise HTTPException(400,'Nur JPEG, PNG, WebP')
        raw=await f.read(8_000_001)
        if len(raw)>8_000_000:raise HTTPException(413,'Bild größer als 8 MB')
        images.append({'type':'image_url','image_url':{'url':'data:'+f.content_type+';base64,'+base64.b64encode(raw).decode(),'detail':'auto'}})
    prompt='''Erstelle eine professionelle, ehrliche deutsche Kleinanzeigen-Anzeige. Gib NUR JSON mit title,description,category,brand,model,condition,price_eur,confidence,pricing_note,questions,search_terms. Titel max 65 Zeichen. Beschreibung einladend, konkrete nur sichtbare Angaben, keine erfundenen Tests/Zubehör/Originalverpackung. Bei unklarer Marke/Modell offen bleiben; Zustand nur anhand sichtbarer Merkmale. Preis nur grobe Schätzung; search_terms ist eine kurze Produktsuche ohne Sonderzeichen. Keine verbotenen oder regulierten Gegenstände inserieren, im Zweifel in questions warnen. Bevorzugt nur Abholung. Hinweise: '''+notes[:1500]
    body={'model':os.getenv('OPENAI_MODEL','gpt-4.1-mini'),'response_format':{'type':'json_object'},'messages':[{'role':'system','content':'Du bist ein erfahrener, vorsichtiger Kleinanzeigen-Texter.'},{'role':'user','content':[{'type':'text','text':prompt},*images]}],'max_tokens':1200,'temperature':0.2}
    try:
        async with httpx.AsyncClient(timeout=115) as c:r=await c.post('https://api.openai.com/v1/chat/completions',headers={'Authorization':'Bearer '+key},json=body)
        if r.status_code!=200:raise HTTPException(502,'OpenAI HTTP '+str(r.status_code)+'. API-Schlüssel, Guthaben und Modellzugriff prüfen.')
        result=normalize_analysis(json.loads(r.json()['choices'][0]['message']['content']))
        result['market']=await market_check(result.get('search_terms') or result.get('title',''))
        if result['market']['sample_size']>=3:
            result['price_eur']=result['market']['median_eur']
            result['pricing_note']='Orientierung am Median von '+str(result['market']['sample_size'])+' sichtbaren Angebotspreisen (keine Verkaufspreise); bitte Zustand prüfen.'
        return result
    except (httpx.TimeoutException,httpx.ConnectError):raise HTTPException(504,'KI nicht erreichbar')
    except (KeyError,ValueError,TypeError):raise HTTPException(502,'KI-Antwort unlesbar')
async def market_check(query):
    """Unverbindliche öffentliche Angebotspreise, keine Umgehung von Zugriffsblockaden."""
    query=re.sub(r'[^\w\s-]',' ',query)[:75].strip()
    result={'sample_size':0,'median_eur':None,'source_url':'https://www.kleinanzeigen.de/s-'+quote(query)+'/k0','note':'Keine belastbaren aktuellen Vergleichspreise abrufbar'}
    if os.getenv('ENABLE_KLEINANZEIGEN_ACCESS','false').lower()!='true' or os.getenv('ENABLE_MARKET_CHECK','false').lower()!='true':
        result['source_url']=None
        return result
    if not query:return result
    try:
        async with httpx.AsyncClient(timeout=10,follow_redirects=True,headers={'User-Agent':'Mozilla/5.0 (compatible; private-price-check/1.0)'}) as c:r=await c.get(result['source_url'])
        if r.status_code!=200:return result
        soup=BeautifulSoup(r.text,'html.parser')
        # Price extraction ONLY within recognizable listing price elements, to avoid random prices.
        prices=[]
        for el in soup.select('.aditem-main--middle--price-shipping--price, .aditem-main--middle--price-shipping, [class*="aditem"] [class*="price"]')[:45]:
            t=el.get_text(' ',strip=True)
            m=re.search(r'(?<!\d)(\d{1,5}(?:[.]\d{3})?)\s*€',t)
            if m:
                v=int(m.group(1).replace('.',''))
                if 2<=v<=25000:prices.append(v)
        if len(prices)>=3:
            result.update(sample_size=len(prices),median_eur=round(statistics.median(prices)),note='Aktuelle sichtbare Angebotspreise, keine abgeschlossenen Verkäufe')
    except Exception:pass
    return result
@app.post('/api/publish')
async def publish(files:list[UploadFile]=File(...),payload:str=Form(...),_=Depends(auth)):
    if os.getenv('ENABLE_KLEINANZEIGEN_ACCESS','false').lower()!='true':raise HTTPException(409,'Automatischer Kleinanzeigen-Zugriff ist deaktiviert. Entwurf speichern oder kopieren.')
    if not (DATA/'account.enc').exists():raise HTTPException(400,'Kleinanzeigen-Konto fehlt in Einstellungen')
    if len(files)<1 or len(files)>8:raise HTTPException(400,'1–8 Bilder')
    if ACTIVE.locked():raise HTTPException(409,'Ein Inserat wird bereits verarbeitet')
    try:data=json.loads(payload)
    except Exception:raise HTTPException(400,'Ungültige Daten')
    if not data.get('review_confirmed'):raise HTTPException(400,'Bestätigung der Angaben fehlt')
    jid=uuid.uuid4().hex; jobdir=DATA/'jobs'/jid;jobdir.mkdir(parents=True,exist_ok=True)
    paths=[]
    for i,f in enumerate(files):
        ext={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'}.get(f.content_type)
        if not ext:raise HTTPException(400,'Bildformat nicht unterstützt')
        raw=await f.read(8_000_001)
        if len(raw)>8_000_000:raise HTTPException(413,'Bild zu groß')
        path=jobdir/f'foto_{i+1}{ext}';path.write_bytes(raw);paths.append(path)
    JOBS[jid]={'status':'running','progress':3,'message':'Inserat ist in der Warteschlange','url':None,'error':None}
    asyncio.create_task(_job(jid,data,paths,jobdir))
    return {'job_id':jid}
async def _job(jid,data,paths,folder):
    from automation import run_listing
    async with ACTIVE:
        def log(n,msg):JOBS[jid].update(progress=n,message=msg)
        try:
            credentials=json.loads(cipher().decrypt((DATA/'account.enc').read_bytes()).decode())
            result=await run_listing(data,paths,credentials,log,folder)
            JOBS[jid].update(status='complete',progress=100,url=result['url'],message='Veröffentlicht')
        except Exception as e:
            JOBS[jid].update(status='failed',error=str(e),message='Automatisierung angehalten – nicht als veröffentlicht bestätigt')
        finally:
            for path in paths:path.unlink(missing_ok=True)
@app.get('/api/job/{jid}')
async def job(jid:str,_=Depends(auth)):
    if jid not in JOBS:raise HTTPException(404,'Job nicht gefunden (nach Server-Neustart werden laufende Jobs nicht fortgeführt)')
    return JOBS[jid]

@app.get('/api/config')
def config(_=Depends(auth)):
    return {'automation_enabled':os.getenv('ENABLE_KLEINANZEIGEN_ACCESS','false').lower()=='true',
            'ai_configured':bool(os.getenv('OPENAI_API_KEY'))}

@app.middleware('http')
async def response_headers(request:Request, call_next):
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Cache-Control']='no-store'
    return response

class UploadLimit:
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        if scope.get('method')=='POST':
            # Auth vor dem Einlesen großer Uploads.
            headers=dict(scope.get('headers',[]))
            offered=headers.get(b'x-app-pin',b'')
            if not hmac.compare_digest(offered,os.getenv('APP_PIN','').encode()):
                await send({'type':'http.response.start','status':401,'headers':[(b'content-type',b'application/json')]})
                return await send({'type':'http.response.body','body':b'{"detail":"App-PIN falsch"}'})
            try:size=int(headers.get(b'content-length',b'0'))
            except ValueError:size=0
            if not 0<size<=65_000_000:
                await send({'type':'http.response.start','status':413,'headers':[(b'content-type',b'application/json')]})
                return await send({'type':'http.response.body','body':b'{"detail":"Upload zu gross oder Content-Length fehlt"}'})
        await self.app(scope,receive,send)

app.add_middleware(UploadLimit)
