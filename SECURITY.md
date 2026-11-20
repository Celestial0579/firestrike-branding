# Sicherheit

## Melden

Bitte Schwachstellen nicht als öffentliches Issue melden. Nutze stattdessen unter „Security“ den Knopf „Report a vulnerability“. Die Meldung sehen dann nur die Betreuer.

## Was hier zählt

- SVG-Dateien mit Skripten, Ereignis-Attributen, Verweisen nach außen oder anderem, das beim Einbinden Code ausführt oder Daten nachlädt
- Fehler in `werkzeuge/marke.py`, durch die beim Erzeugen oder Prüfen Dateien außerhalb des Repos geschrieben oder fremder Code ausgeführt wird
- Exporte, die im Zielsystem Anordnung oder Sichtbarkeit verändern, etwa einen Hinweis auf der Anmeldeseite verdecken

## Unterstützter Stand

Nur der aktuelle Stand von `main`.
