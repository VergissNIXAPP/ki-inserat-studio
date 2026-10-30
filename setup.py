#!/usr/bin/env python3
"""Einmalige Einrichtung auf dem Zielserver; keine externen Aufrufe."""
from pathlib import Path
import base64,getpass,os,re,secrets
os.umask(0o077)
root=Path(__file__).resolve().parent
path=root/'.env'
if path.exists():raise SystemExit('.env existiert bereits und bleibt unverändert. Bei Bedarf mit nano .env bearbeiten.')
domain=input('Deine Subdomain, z.B. inserat.meinedomain.de: ').strip().lower()
if not re.fullmatch(r'(?=.{1,253}$)[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}',domain):raise SystemExit('Bitte Domain ohne https:// und ohne Pfad eingeben.')
key=getpass.getpass('OpenAI-API-Schlüssel (Eingabe bleibt unsichtbar): ').strip()
if not key or any(c.isspace() for c in key) or any(c in key for c in "'\"#$") :raise SystemExit('Ungültiges Schlüsselformat.')
pin=secrets.token_urlsafe(32)
fernet=base64.urlsafe_b64encode(os.urandom(32)).decode()
text=(root/'.env.example').read_text().replace('inserat.example.de',domain).replace('APP_PIN=\n','APP_PIN='+pin+'\n').replace('OPENAI_API_KEY=\n','OPENAI_API_KEY='+key+'\n').replace('CREDENTIAL_KEY=\n','CREDENTIAL_KEY='+fernet+'\n')
with path.open('x') as f:f.write(text)
path.chmod(0o600)
print('Konfiguration gespeichert. Deine private App-PIN:')
print(pin)
print('Diese PIN im Passwortmanager speichern. Nicht auf GitHub hochladen.')
print('Nächster Schritt: docker compose up -d --build')
