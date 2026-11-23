# Größen und Abstände

Erzeugt von `werkzeuge/marke.py` aus `tokens/firestrike.json`, nicht von Hand ändern.

## Schriftgrößen

Eine fließende Größe wächst zwischen 320px und 64rem Fensterbreite gleichmäßig von „ab“ auf „bis“. So rechnet auch WordPress. Apps nehmen die feste Größe in Pixeln (1rem = 16 px).

| Rolle | Fest | Fließend ab | bis | Apps (px) | CSS | WordPress |
|---|---:|---:|---:|---:|---|---|
| Klein | 0,875rem | – | – | 14 | `--fs-groesse-klein` | `small` |
| Normal | 1,0625rem | 0,875rem | 1,0625rem | 17 | `--fs-groesse-normal` | `medium` |
| Groß | 1,5rem | 1,3rem | 1,6rem | 24 | `--fs-groesse-gross` | `large` |
| Sehr groß | 2,2rem | 1,8rem | 2,6rem | 35,2 | `--fs-groesse-sehr-gross` | `x-large` |
| Titel | 3rem | 2,2rem | 3,4rem | 48 | `--fs-groesse-titel` | `xx-large` |

## Abstände

| Stufe | Wert | Apps (px) | CSS | WordPress |
|---|---:|---:|---|---|
| 10 | 0,35rem | 5,6 | `--fs-abstand-10` | `10` |
| 20 | 0,7rem | 11,2 | `--fs-abstand-20` | `20` |
| 30 | 1,1rem | 17,6 | `--fs-abstand-30` | `30` |
| 40 | 1,7rem | 27,2 | `--fs-abstand-40` | `40` |
| 50 | 2,6rem | 41,6 | `--fs-abstand-50` | `50` |
| 60 | 4rem | 64 | `--fs-abstand-60` | `60` |
| 70 | 6rem | 96 | `--fs-abstand-70` | `70` |

## Satz

| Wofür | Wert | CSS |
|---|---:|---|
| Zeilenhöhe im Fließtext | 1,65 | `--fs-zeilenhoehe-text` |
| Zeilenhöhe der Überschriften | 1,2 | `--fs-zeilenhoehe-ueberschrift` |
| Stärke der Überschriften | 600 | `--fs-staerke-ueberschrift` |
