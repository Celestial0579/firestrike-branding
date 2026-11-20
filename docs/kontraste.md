# Kontraste

Erzeugt von `werkzeuge/marke.py` aus `tokens/firestrike.json`, nicht von Hand ändern.
Gerechnet nach WCAG 2.2 aus der relativen Leuchtdichte, abgerundet auf zwei Stellen.
Die Prüfung schlägt fehl, sobald ein Paar in einem der beiden Themen unter seinem Mindestwert liegt.

| Vorne | Hinten | Hell | Dunkel | Mindestens | Wofür |
|---|---|---:|---:|---:|---|
| Text | Grund | 14,69:1 | 15,01:1 | 4,5:1 | Fließtext |
| Text | Fläche | 16,81:1 | 13,71:1 | 4,5:1 | Fließtext |
| Text | Fläche tief | 13,25:1 | 11,98:1 | 4,5:1 | Fließtext |
| Text leise | Grund | 5,63:1 | 7,84:1 | 4,5:1 | Nebentext |
| Text leise | Fläche | 6,44:1 | 7,16:1 | 4,5:1 | Nebentext |
| Text leise | Fläche tief | 5,08:1 | 6,26:1 | 4,5:1 | Nebentext |
| Stahl tief | Grund | 12,59:1 | 10,26:1 | 4,5:1 | Überschriften |
| Stahl tief | Fläche | 14,40:1 | 9,37:1 | 4,5:1 | Überschriften |
| Stahl tief | Fläche tief | 11,35:1 | 8,19:1 | 4,5:1 | Überschriften |
| Glut | Grund | 5,12:1 | 5,79:1 | 4,5:1 | Verweise |
| Glut | Fläche | 5,86:1 | 5,28:1 | 4,5:1 | Verweise |
| Glut | Fläche tief | 4,62:1 | 4,62:1 | 4,5:1 | Verweise |
| Stahl | Grund | 9,18:1 | 5,65:1 | 4,5:1 | Verweise beim Überfahren |
| Stahl | Fläche | 10,50:1 | 5,16:1 | 4,5:1 | Verweise beim Überfahren |
| Stahl | Fläche tief | 8,28:1 | 4,51:1 | 4,5:1 | Verweise beim Überfahren |
| Fläche | Stahl | 10,50:1 | 5,16:1 | 4,5:1 | Schrift auf Schaltflächen |
| Fläche | Glut | 5,86:1 | 5,28:1 | 4,5:1 | Schrift auf Schaltflächen |
| Fokus | Grund | 5,12:1 | 9,90:1 | 3:1 | Fokusrahmen |
| Fokus | Fläche | 5,86:1 | 9,04:1 | 3:1 | Fokusrahmen |
| Fokus | Fläche tief | 4,62:1 | 7,90:1 | 3:1 | Fokusrahmen |

## Nur Schmuck

Diese Paare liegen mindestens in einem Thema unter 4,5:1. Sie tragen darum nie Text oder Bedeutung.

| Vorne | Hinten | Hell | Dunkel | Hinweis |
|---|---|---:|---:|---|
| Funke | Grund | 1,88:1 | 9,90:1 | auf hellem Grund nur Linien und Marker, nie Text |
| Linie | Fläche | 1,62:1 | 1,54:1 | nie die einzige Grenze eines Bedienelements |
