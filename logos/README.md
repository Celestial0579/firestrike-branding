# Logos

Wortmarke, Bildzeichen und Symbol von Firestrike. **Nicht unter der MIT-Lizenz**, siehe [MARKE.md](../MARKE.md). Wann welche Datei passt, steht in [docs/nutzung.md](../docs/nutzung.md#logos).

Die einfarbigen Fassungen (`*-mono-*.svg`) erzeugt `werkzeuge/marke.py` aus den farbigen. Bitte nicht von Hand ändern.

## Wortmarke als Pfade

Unter [`pfade/`](pfade) liegen dieselben Logos mit der Wortmarke als Pfaden statt als Text. Sie sehen auf jedem System gleich aus, weil keine Schrift mehr nötig ist. Die Umrisse stammen aus Liberation Sans Bold (SIL Open Font License 1.1), die metrisch Arial entspricht. Laufweite 2,6, Stärke 700 und Lage bleiben wie in der Text-Fassung.

- Erzeugt mit `python3 werkzeuge/marke.py wortmarke LiberationSans-Bold.ttf`, danach `erzeugen` für die einfarbigen.
- `pfade/quelle.json` nennt Schrift, Lizenz und die Prüfsummen der Text-Logos. Ändert sich ein Text-Logo, meldet `pruefen` die Pfad-Fassung als veraltet.
- Noch ein Entwurf: Die Fassungen mit Text bleiben die gültigen, bis die Pfad-Fassung freigegeben ist. Danach ersetzt sie die Text-Fassung.
