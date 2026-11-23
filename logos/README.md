# Logos

Wortmarke, Bildzeichen und Symbol von Firestrike. **Nicht unter der MIT-Lizenz**, siehe [MARKE.md](../MARKE.md). Wann welche Datei passt, steht in [docs/nutzung.md](../docs/nutzung.md#logos).

Die einfarbigen Fassungen (`*-mono-*.svg`) erzeugt `werkzeuge/marke.py` aus den farbigen. Bitte nicht von Hand ändern.

## Wortmarke als Pfade

Die Logos tragen die Wortmarke als Pfade, nicht als Text. Sie sehen darum auf jedem System gleich aus, und es wird keine Schrift gebraucht. Die Umrisse stammen aus Liberation Sans Bold (SIL Open Font License 1.1), die metrisch Arial entspricht. Laufweite 2,6, Stärke 700 und Lage sind dieselben wie in der früheren Text-Fassung.

- Die Text-Fassungen liegen als Quelle unter [`quellen/`](quellen) (`*-text.svg`). Wer Laufweite oder Lage ändern will, ändert dort und erzeugt neu: `python3 werkzeuge/marke.py wortmarke LiberationSans-Bold.ttf`, danach `erzeugen` für die einfarbigen.
- `quellen/quelle.json` nennt Schrift, Lizenz und die Prüfsummen der Text-Fassungen. Ändert sich eine davon, meldet `pruefen` die Logos als veraltet.
- Gerendert decken sich Text- und Pfad-Fassung bis aufs Antialiasing (bei 1000 × 200 Pixeln höchstens 18 von 255 Abweichung).
