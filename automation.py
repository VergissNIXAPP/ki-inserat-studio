"""Best-effort Playwright integration. Never bypass captchas, anti-bot checks, or 2FA."""
import asyncio, os, re
from pathlib import Path
from playwright.async_api import async_playwright

BASE='https://www.kleinanzeigen.de'
POST=BASE+'/p-anzeige-aufgeben.html'

async def run_listing(data, photos, credentials, log, state_dir:Path):
    async def progress(p, detail):
        log(p,detail)
    async with async_playwright() as p:
        path=os.getenv('CHROMIUM_PATH','')
        browser=await p.chromium.launch(headless=True, executable_path=path if path and Path(path).is_file() else None,
            args=['--no-sandbox'] if os.getenv('CHROME_NO_SANDBOX')=='1' else [])
        context=await browser.new_context(locale='de-DE',viewport={'width':1280,'height':920},accept_downloads=False)
        page=await context.new_page()
        try:
            await progress(12,'Kleinanzeigen wird geöffnet')
            await page.goto(POST,wait_until='domcontentloaded',timeout=45000)
            await page.wait_for_timeout(1700)
            # Consent dialog (only visible and exact when possible).
            for pattern in ['Alle akzeptieren','Akzeptieren und weiter','Auswahl speichern','Nur notwendige Cookies']:
                try:
                    b=page.get_by_role('button',name=pattern,exact=True)
                    if await b.count() and await b.first.is_visible():
                        await b.first.click(timeout=2500);break
                except Exception: pass
            await progress(22,'Anmeldestatus wird geprüft')
            await complete_login(page, credentials, progress, state_dir)
            if await challenge(page):
                raise RuntimeError('Kleinanzeigen verlangt CAPTCHA, 2FA oder eine manuelle Bestätigung. Bitte zuerst im offiziellen Browser anmelden; die App umgeht diese Prüfungen nicht.')
            await progress(40,'Inseratsformular wird befüllt')
            title=(data.get('title') or '').strip()[:65]
            description=(data.get('description') or '').strip()
            price=int(data['price_eur'])
            if not title or not description or price<=0: raise RuntimeError('Titel, Beschreibung oder Preis fehlen.')
            await fill_first(page,['input[name=title]','input[id*=title]','input[placeholder*=Titel]'],title,required=True)
            await fill_first(page,['textarea[name=description]','textarea[id*=description]','textarea[placeholder*=Beschreibung]'],description,required=True)
            await fill_first(page,['input[name=price]','input[id*=price]','input[placeholder*=Preis]'],str(price),required=True)
            await progress(58,'Bilder werden hochgeladen')
            loc=page.locator('input[type=file]')
            if await loc.count()==0: raise RuntimeError('Foto-Uploader nicht erkannt. Formular wurde möglicherweise geändert.')
            await loc.first.set_input_files([str(x) for x in photos])
            await page.wait_for_timeout(1400)
            await progress(71,'Abholung und Direktkauf werden geprüft')
            pickup=await select_choice(page,['Nur Abholung','Abholung'])
            direct=await select_choice(page,['Nein, „Direkt kaufen“ nicht nutzen','Nein, "Direkt kaufen" nicht nutzen','Direkt kaufen nicht nutzen'])
            if not pickup or not direct:
                raise RuntimeError('Versand/Direktkauf konnten nicht BEIDE eindeutig deaktiviert werden. Keine Veröffentlichung. Bitte Formular im offiziellen Browser prüfen.')
            await progress(83,'Kategorie und Pflichtfelder werden geprüft')
            # Category is often chosen via a multi-step flow. Do not fabricate category IDs.
            if await challenge(page): raise RuntimeError('Kleinanzeigen benötigt eine manuelle Sicherheitsbestätigung.')
            if os.getenv('ALLOW_AUTO_PUBLISH','false').lower()!='true':
                raise RuntimeError('Testlauf beendet: ALLOW_AUTO_PUBLISH ist nicht true. Keine Anzeige wurde veröffentlicht.')
            await progress(92,'Finale Veröffentlichung wird versucht')
            b=page.get_by_role('button',name=re.compile(r'(Anzeige aufgeben|Anzeige veröffentlichen|Jetzt inserieren|Veröffentlichen)',re.I))
            if not await b.count() or not await b.first.is_enabled():
                raise RuntimeError('Veröffentlichen-Button fehlt oder ist deaktiviert; möglicherweise sind weitere Pflichtfelder nötig.')
            await b.first.click(timeout=10000)
            await page.wait_for_timeout(3000)
            if await challenge(page): raise RuntimeError('Nach dem Absenden ist eine manuelle Verifizierung erforderlich. Status unklar; bitte Konto prüfen.')
            url=page.url
            text=(await page.locator('body').inner_text())[:3500].lower()
            success=('erfolgreich' in text and ('anzeige' in text or 'inserat' in text)) or ('/s-anzeige/' in url)
            if not success: raise RuntimeError('Absenden versucht, Veröffentlichung NICHT bestätigt. Vor erneutem Versuch bitte im Konto prüfen, um Doppelanzeigen zu vermeiden. Aktuelle URL: '+url)
            await progress(100,'Veröffentlichung bestätigt')
            return {'published':True,'url':url}
        finally:
            try: await page.screenshot(path=str(state_dir/'last_browser.png'),full_page=True,timeout=6000)
            except Exception: pass
            await browser.close()

async def fill_first(page, selectors, value, required=False):
    for s in selectors:
        try:
            a=page.locator(s).first
            if await a.count() and await a.is_visible():
                await a.fill(value,timeout=2500);return True
        except Exception: pass
    if required: raise RuntimeError('Formularfeld nicht gefunden: '+selectors[0])
    return False

async def click_first(page, selectors):
    for s in selectors:
        try:
            a=page.locator(s).first
            if await a.count() and await a.is_visible():
                await a.click(timeout=2500);return True
        except Exception: pass
    return False

async def select_choice(page, names):
    for name in names:
        for role in ['radio','button','checkbox']:
            try:
                el=page.get_by_role(role,name=name,exact=True).first
                if await el.count() and await el.is_visible():
                    if role=='radio': await el.check(timeout=2500)
                    elif role=='checkbox': await el.check(timeout=2500)
                    else: await el.click(timeout=2500)
                    return True
            except Exception: pass
        try:
            el=page.get_by_text(name,exact=True).first
            if await el.count() and await el.is_visible():
                await el.click(timeout=2500);return True
        except Exception: pass
    return False

async def challenge(page):
    from app_utils import is_access_block
    try:
        if is_access_block((await page.locator('body').inner_text())[:12000]):
            raise RuntimeError('Kleinanzeigen hat den Zugriff gesperrt. Keine Wiederholung und keine weiteren Anmeldeschritte. Sperre abwarten oder Support kontaktieren.')
    except RuntimeError:raise
    except Exception:pass
    url=page.url.lower()
    if any(k in url for k in ['captcha','challenge','verify']): return True
    try:
        body=(await page.locator('body').inner_text())[:3500].lower()
        return any(k in body for k in ['captcha','ich bin kein roboter','sicherheitsprüfung','bestätigungscode eingeben','zweifaktor'])
    except Exception: return False

# Login-Fix v1: sichtbare Formularfelder statt URL-Namen erkennen.
async def complete_login(page, credentials, progress, state_dir=None):
    email_selector = 'input[type="email"], input[autocomplete="username"], input[name="email"], input[id*="email" i]'
    password_selector = 'input[type="password"]'
    title_selector = 'input[name="title"], input[id*="title"], input[placeholder*="Titel"]'

    async def visible(selector):
        loc = page.locator(selector)
        found = []
        for i in range(await loc.count()):
            item = loc.nth(i)
            if await item.is_visible(): found.append(item)
        if len(found) > 1:
            raise RuntimeError('Anmeldefeld nicht eindeutig. Bitte last_browser.png prüfen.')
        return found[0] if found else None

    async def wait_field(selector, seconds=18):
        for _ in range(seconds * 2):
            if await challenge(page):
                raise RuntimeError('Anmeldung benötigt eine Sicherheitsprüfung oder einen Code. Automatisierung angehalten; keine Anzeige veröffentlicht.')
            item = await visible(selector)
            if item is not None: return item
            await page.wait_for_timeout(500)
        return None

    async def button(names):
        for name in names:
            loc = page.get_by_role('button', name=name, exact=True)
            matches = []
            for i in range(await loc.count()):
                item = loc.nth(i)
                if await item.is_visible() and await item.is_enabled(): matches.append(item)
            if len(matches) == 1:
                await matches[0].click(timeout=7000)
                return
        raise RuntimeError('Anmeldebutton nicht eindeutig gefunden. Bitte last_browser.png prüfen.')

    # Ein bereits sichtbares Inseratsformular benötigt keinen Login.
    if await visible(title_selector) is not None: return
    email = await wait_field(email_selector, 12)
    if email is None:
        if await visible(title_selector) is not None: return
        raise RuntimeError('Weder E-Mail-Feld noch Inseratsformular erkannt. Bitte last_browser.png prüfen.')
    await progress(25, 'E-Mail-Adresse wird eingegeben')
    await email.fill(credentials['email'], timeout=7000)
    password = await visible(password_selector)
    if password is None:
        await button(['Weiter'])
        password = await wait_field(password_selector)
    if password is None:
        raise RuntimeError('Nach der E-Mail ist kein Passwortfeld erschienen. E-Mail, Anmeldehinweis oder Bestätigungsanforderung in last_browser.png prüfen.')
    await progress(30, 'Passwort wird eingegeben')
    await password.fill(credentials['password'], timeout=7000)
    # Login-Wartefix v2: keine Weiterleitung nur wegen verschwundenem Passwortfeld.
    from urllib.parse import urlsplit
    initial_url = page.url
    await button(['Einloggen', 'Anmelden', 'Login', 'Weiter'])
    stable_url = None
    stable_count = 0
    email_count = 0
    for _ in range(60):
        await page.wait_for_timeout(500)
        if await challenge(page):
            raise RuntimeError('Kleinanzeigen verlangt eine Sicherheitsbestätigung. Keine Anzeige veröffentlicht; last_browser.png zeigt den aktuellen Schritt.')
        if await visible(title_selector) is not None:
            return
        email_visible = await visible(email_selector) is not None
        password_visible = await visible(password_selector) is not None
        email_count = email_count + 1 if email_visible and not password_visible else 0
        if email_count >= 12:
            raise RuntimeError('Nach dem Einloggen wird wieder die E-Mail-Abfrage angezeigt. Die Sitzung wurde nicht übernommen oder die Anmeldung benötigt einen weiteren Schritt. Bitte last_browser.png prüfen.')
        # Nur eine stabile Rückkehr zur eigentlichen Kleinanzeigen-Seite erlaubt Weiterleitung.
        current = page.url
        parts = urlsplit(current)
        returned = (parts.hostname in ('www.kleinanzeigen.de', 'kleinanzeigen.de')
                    and current != initial_url
                    and not any(x in parts.path.lower() for x in ('login', 'einloggen', 'auth', 'verify', 'challenge'))
                    and not email_visible and not password_visible)
        if returned:
            stable_count = stable_count + 1 if stable_url == current else 1
            stable_url = current
            if stable_count >= 8:
                if state_dir is not None:
                    await page.screenshot(path=str(state_dir/'login_vor_weiterleitung.png'), full_page=True, timeout=6000)
                await page.goto(POST, wait_until='domcontentloaded', timeout=45000)
                if await wait_field(title_selector, 20) is not None: return
                raise RuntimeError('Rückkehr von der Anmeldung erkannt, aber Inseratsformular fehlt. Bitte last_browser.png UND login_vor_weiterleitung.png prüfen. Anmeldung nicht bestätigt.')
        else:
            stable_url = None
            stable_count = 0
    raise RuntimeError('Anmeldung nach 30 Sekunden nicht abgeschlossen. Keine Weiterleitung erzwungen. Bitte den Hinweis in last_browser.png prüfen; dort steht der tatsächliche Anmeldeschritt.')


