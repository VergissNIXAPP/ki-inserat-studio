# Prüfbericht – Cloud-Migration

30.10.2026

- Python-Syntaxprüfung der Anwendungs- und Einrichtungsskripte bestanden.
- JavaScript-Syntaxprüfung der Handy-Oberfläche bestanden.
- Drei zusätzliche FastAPI-Integrationstests mit simuliertem KI-Dienst bestanden: Authentifizierung, gesperrte Konto-/Veröffentlichungs-Endpunkte und Fotoanalyse ohne Kleinanzeigen-Preisabruf. Insgesamt sieben Tests bestanden.
- Vier automatisierte Testgruppen für die Normalisierung von KI-Antworten, Preiswerten, Rückfragen und die Erkennung von Zugangssperren bestanden.
- Login-Reparaturen aus der vorherigen Version übernommen. Diese wurden bereits mit simulierten Browserzuständen geprüft, nicht mit einem echten Kleinanzeigen-Konto.

Nicht ausgeführt: echter Docker-Image-Build (Docker in der Entwicklungsumgebung nicht vorhanden), Deployment auf VPS, DNS/HTTPS-Zertifikatsprüfung, echter OpenAI-Aufruf, Live-Anmeldung oder Veröffentlichung auf Kleinanzeigen.

Die IP-Sperre ist bekannt. Es wurden keine neuen Zugriffsversuche auf Kleinanzeigen ausgeführt. In der Cloud-Voreinstellung sind alle automatischen Kleinanzeigen-Zugriffe deaktiviert.

GitHub Actions führt Syntax- und Offline-Tests nach dem Upload aus. Den aktuellen Status im Actions-Tab prüfen.
