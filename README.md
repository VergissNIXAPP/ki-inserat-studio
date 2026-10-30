# KI Inserat Studio – GitHub & Cloud

Deine mobile Web-App läuft ohne Raspberry Pi. GitHub enthält den Quellcode. Ein eigener Linux-Server führt Python, die Bildanalyse-Anfragen und bei später freigegebener Nutzung den experimentellen Browseradapter aus.

**GitHub Pages ist nicht ausreichend:** Es führt diesen Python-Server nicht aus. GitHub Actions ist ebenfalls kein dauerhaft laufender Webserver. Dieses Projekt nutzt deshalb Docker Compose auf einem VPS (gemieteter Linux-Server).

## Was diese Version kann

- Kamera/Fotogalerie auf dem Handy, bis zu 8 Bilder.
- OpenAI-Bildanalyse, Titel, Beschreibung, Rückfragen und unbestätigte Preisschätzung.
- Texte bearbeiten, kopieren und als Textdatei herunterladen.
- Geschützter API-Zugang mit zufälliger App-PIN; HTTPS über Caddy.
- Automatischer Start nach Serverneustart durch Docker.
- Daten in einem Docker-Volume statt in einem Raspberry-Pi-Ordner.
- Frühere Korrekturen für Rückfragenformat und zweistufige Anmeldung integriert.
- GitHub-Prüfung der Python-Dateien bei Push.

**Wegen der beobachteten Kleinanzeigen-IP-Sperre sind automatische Kleinanzeigen-Zugriffe standardmäßig vollständig ausgeschaltet.** Auch der Preisabruf ist ausgeschaltet. Die KI-Analyse greift nur auf OpenAI zu. Die Cloud-Migration ist keine Aufhebung der Sperre und darf nicht als Wiederholung blockierter Zugriffe über eine neue IP verstanden werden. Der Browseradapter ist unbestätigt und nicht Voraussetzung für die Fotoanalyse.

## A. Was du brauchst

1. Das Repository `VergissNIXAPP/ki-inserat-studio`. Es wurde öffentlich angelegt; der Quellcode enthält keine persönlichen Zugangsdaten.
2. Einen Linux-VPS, z.B. Ubuntu 24.04 LTS mit 64-bit und Docker-Unterstützung. Plane für Chromium etwa 4 GB RAM und 15 GB freien Speicher ein; das ist eine Planungsgröße, kein gemessener Mindestwert. Anbieter und Tarif kannst du selbst wählen. Hosting kann laufende Kosten verursachen.
3. Eine Domain/Subdomain, z.B. `inserat.deinedomain.de`, deren DNS du bearbeiten kannst.
4. Einen OpenAI-API-Schlüssel mit API-Guthaben. Die Bilder werden an OpenAI übertragen. ChatGPT-Zugangsdaten sind kein API-Schlüssel.

Das Repository enthält den Programmcode. Ein Laufzeitserver wurde nicht gebucht oder bereitgestellt; der Upload auf GitHub startet die App noch nicht.

## B. Quellcode auf GitHub

Repository: https://github.com/VergissNIXAPP/ki-inserat-studio

Der Code ist bereits hier vorhanden. Für die Installation mit Abschnitt C fortfahren. Die folgenden Upload-Schritte sind nur für eine eigene Kopie nötig.

### Optional: eigene Kopie hochladen

1. ZIP entpacken. Öffne den Ordner `ki-inserat-cloud`.
2. Auf GitHub ein neues Repository namens `ki-inserat-studio` erstellen. Sichtbarkeit: **Private**. Für den folgenden Upload kein zusätzliches README erzeugen.
3. Im leeren Repository den Link zum Hochladen vorhandener Dateien verwenden.
4. **Den Inhalt** des entpackten Ordners hochladen: `server.py`, `Dockerfile`, `compose.yaml`, `static/` usw. Nicht nur die ZIP-Datei hochladen und nicht noch eine zusätzliche Ordnerebene anlegen.
5. Änderungen speichern/committen. Im Repository-Hauptverzeichnis müssen `Dockerfile` und `compose.yaml` sichtbar sein.

Versteckte Dateien wie `.github`, `.gitignore`, `.dockerignore` und `.env.example` können beim Datei-Upload übersehen werden. Am zuverlässigsten ist GitHub Desktop auf deinem PC: „Add an Existing Repository“ nach lokalem `git init`, dann „Publish repository“, „Keep this code private“ aktivieren. Alternativ Git im Terminal:

```bash
cd ki-inserat-cloud
git init
git add .
git commit -m "Cloud-Version des Inserat Studios"
git branch -M main
git remote add origin https://github.com/VergissNIXAPP/ki-inserat-studio.git
git push -u origin main
```

`DEIN-NAME` ersetzen. GitHub verlangt eine unterstützte Anmeldung, z.B. GitHub Desktop oder ein Zugriffstoken; das normale Kontopasswort ist für Git-HTTPS nicht vorgesehen. Tokens nie in die Repository-URL oder in Nachrichten einsetzen.

**Nie deine bestehende `.env`, `data/`, gespeicherte Konten oder Browser-Fehlerbilder hochladen.** Das ZIP enthält keine deiner Zugangsdaten. Die Ignore-Dateien schützen Git/Docker; beim manuellen Web-Upload musst du selbst darauf achten.

## C. Server vorbereiten

Beim Anbieter einen Linux-Server anlegen. SSH-Verbindungsdaten kommen vom Anbieter. Für einfache Schritte im Folgenden wird ein Benutzer mit `sudo` vorausgesetzt; bei Root-Anmeldung das `sudo` gegebenenfalls weglassen.

Am PC-Terminal:

```bash
ssh DEIN-SERVERBENUTZER@DEINE-SERVER-IP
```

Auf dem Server:

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates python3
```

Docker Engine mit Compose nach offizieller Anleitung installieren:
https://docs.docker.com/engine/install/ubuntu/

Für einen frischen, privaten Server gibt es auch das offizielle Komfortskript. Lade es herunter, prüfe es und führe es aus:

```bash
curl -fsSL https://get.docker.com -o install-docker.sh
less install-docker.sh
sudo sh install-docker.sh
sudo systemctl enable --now docker
sudo docker compose version
```

`less` mit `q` verlassen. Bei bereits installiertem Docker nicht erneut installieren. Die Ausgabe des letzten Befehls muss eine Compose-Version zeigen.

## D. Privates Repository auf dem Server abrufen

```bash
git clone https://github.com/VergissNIXAPP/ki-inserat-studio.git
cd ki-inserat-studio
```

Bei HTTPS-Anmeldung das Token nur in die verdeckte Passwortabfrage eingeben. Am besten einen nur für dieses Repository leseberechtigten Zugriff oder einen Deploy-Key benutzen. Anleitung: https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys

Alternativ kannst du den entpackten Quellcode mit WinSCP auf den Server kopieren. Dann brauchst du zum ersten Start keine Git-Anmeldedaten auf dem Server. GitHub bleibt trotzdem die Quelle für deine Versionen.

## E. Domain und Firewall

In der DNS-Verwaltung deiner Domain einen **A-Eintrag** erstellen:

- Name: `inserat`
- Ziel: öffentliche IPv4-Adresse deines neuen Servers.

Entferne einen widersprüchlichen AAAA-Eintrag, falls du IPv6 nicht eingerichtet hast. Verwende zunächst direkten DNS-Zugriff ohne vorgeschalteten CDN-Proxy. Die DNS-Änderung muss wirksam sein, bevor Caddy das Zertifikat ausstellen kann.

Im Anbieter-Firewallmenü freigeben:

- TCP 22 für SSH, möglichst auf deine eigene IP beschränkt.
- TCP 80 und 443 für HTTPS-Einrichtung und Webzugriff.

**Port 8000 nicht öffentlich freigeben.** Compose veröffentlicht nur den HTTPS-Proxy. Verwende nach dem Start ausschließlich die HTTPS-Adresse mit deinem echten Domainnamen.

## F. App einrichten und starten

Im Repository-Ordner auf dem Server:

```bash
python3 setup.py
```

Du wirst nach deiner Subdomain und dem OpenAI-API-Schlüssel gefragt. Die Schlüsseleingabe bleibt unsichtbar. Das Skript erzeugt `.env`, einen Verschlüsselungsschlüssel und eine lange **App-PIN**. Diese PIN in deinem Passwortmanager speichern. Bestehende `.env`-Dateien werden nicht überschrieben.

Dann:

```bash
sudo docker compose up -d --build
sudo docker compose ps
sudo docker compose logs --tail=60 web app
```

Der erste Build lädt Python-Pakete und Chromium und dauert einige Minuten. Es muss anschließend `app` als laufend/healthy und `web` als laufend erscheinen. Bei Zertifikatsfehlern Domain/DNS und Ports 80/443 prüfen.

## G. Auf dem Handy öffnen

1. `https://DEINE-ECHTE-SUBDOMAIN` in Safari oder Chrome öffnen.
2. Die generierte App-PIN eingeben.
3. **„Ohne Konto fortfahren (nur Entwürfe)“** wählen. Kleinanzeigen-Zugangsdaten sind für die Bildanalyse nicht erforderlich.
4. Foto aufnehmen, analysieren, Text und Preis prüfen.
5. „Entwurf herunterladen“ oder „Nur Entwurf anzeigen“ → „Titel + Beschreibung kopieren“ verwenden.
6. Für ein App-Symbol auf dem iPhone: Safari → Teilen → Zum Home-Bildschirm.

Der Pi kann ausgeschaltet bleiben. Keine Tailscale-App nötig. Der neue Server muss laufen. Die App-PIN schützt die APIs; die Login-Oberfläche selbst ist öffentlich erreichbar. Wer die PIN kennt, kann deine kostenpflichtige API benutzen. Nicht teilen.

## H. Automatisierung und vorhandene IP-Sperre

Die Einstellungen sind absichtlich:

```dotenv
ENABLE_KLEINANZEIGEN_ACCESS=false
ENABLE_MARKET_CHECK=false
ALLOW_AUTO_PUBLISH=false
```

Der erste Schalter sperrt sowohl Kontospeicherung als auch den Veröffentlichungs-Endpunkt und den automatischen Preisabruf. Die Datei `automation.py` ist als experimenteller Bestandscode enthalten. Sie erkennt jetzt auch die beobachtete IP-Sperrmeldung und bricht ab. Keine Fingerprint-Tarnung, Proxy-Rotation oder CAPTCHA-Umgehung ist enthalten.

Nicht auf dem neuen Server weiterprobieren, um die bestehende Sperre zu umgehen. Erst Sperrklärung über Kleinanzeigen abwarten. Ein später freigegebener Betrieb müsste separat live geprüft werden; Kategorie, Login, Pflichtfelder, Cookies und erfolgreiche Veröffentlichung sind weiterhin nicht verifiziert. Dieses Paket verspricht keinen funktionierenden Vollautoposter.

## I. Aktualisieren, stoppen, Daten sichern

Quellcode-Update nach einem GitHub-Push:

```bash
git pull --ff-only
sudo docker compose up -d --build
```

Änderungen an `.env` werden erst nach `sudo docker compose up -d --force-recreate app` vom laufenden Container übernommen. Keine Schlüssel in Logs oder Screenshots teilen.

Stoppen / starten:

```bash
sudo docker compose stop
sudo docker compose start
```

Die Container starten nach einem Neustart des Servers automatisch, wenn Docker aktiviert ist. GitHub-Pushes lösen **keine** automatische Produktivbereitstellung aus; dafür ist der Update-Befehl nötig.

Daten liegen im Docker-Volume `ki-inserat_app_data`, Zertifikate in `ki-inserat_caddy_data`. `.env` separat sichern und verschlüsselt aufbewahren. `docker compose down` erhält Volumes; **`docker compose down -v` löscht sie**. Keine `-v`-Option verwenden, wenn Daten erhalten bleiben sollen.

Ein Anzeigenentwurf im Handy-Browser ist nicht dauerhaft gespeichert. Vor Neuladen die Textdatei herunterladen. Hintergrundjobs liegen im Arbeitsspeicher; der Server darf während eines Jobs nicht neu gestartet werden.

## J. Kosten und Prüfumfang

Mögliche Kosten: VPS, Domain und OpenAI-API. Keine aktuellen Anbieterpreise werden zugesichert; aktuelle Hosting-Dokumentation konnte in dieser Sitzung nicht online abgerufen werden.

Siehe `TESTBERICHT.md` für die tatsächlich ausgeführten Prüfungen. Docker-Build, Zertifikatsausstellung, echter Smartphone-Kamerazugriff, OpenAI und Kleinanzeigen wurden nicht live getestet. Das Paket ist vorbereitet, nicht bereits auf deinem Server installiert.
