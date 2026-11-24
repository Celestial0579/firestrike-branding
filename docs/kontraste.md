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

## WinUI-Akzentreihe

Die Stufen entstehen aus Glut und Funke (`winui.akzentreihe` in den Tokens). WinUI nimmt im hellen Thema Dark1 für Akzentflächen und Dark2, Dark3 und Dark1 für Verweise, im dunklen Thema Light2 für Flächen und Light3 und Light2 für Verweise. Auf Akzentflächen schreibt WinUI weiß (hell) und schwarz (dunkel). Markierten Text schreibt es in beiden Themen weiß auf SystemAccentColor. Auf die übrigen AccentAA-Flächen schreibt es weiß (hell: Dark2, SystemAccentColor) und schwarz (dunkel: Light3, Light1). Jedes Paar braucht 4,5:1.

| Stufe | Farbe |
|---|---|
| SystemAccentColor | #A24C18 |
| SystemAccentColorLight1 | #CF6028 |
| SystemAccentColorLight2 | #DB7745 |
| SystemAccentColorLight3 | #F2B558 |
| SystemAccentColorDark1 | #A24C18 |
| SystemAccentColorDark2 | #A24C18 |
| SystemAccentColorDark3 | #7E3B13 |

| Thema | Vorne | Hinten | Kontrast | Wofür |
|---|---|---|---:|---|
| hell | SystemAccentColorDark2 #A24C18 | Grund #EFF0ED | 5,12:1 | Verweis |
| hell | SystemAccentColorDark2 #A24C18 | Fläche #FFFFFF | 5,86:1 | Verweis |
| hell | SystemAccentColorDark2 #A24C18 | Fläche tief #E3E5E1 | 4,62:1 | Verweis |
| hell | SystemAccentColorDark3 #7E3B13 | Grund #EFF0ED | 7,27:1 | Verweis |
| hell | SystemAccentColorDark3 #7E3B13 | Fläche #FFFFFF | 8,32:1 | Verweis |
| hell | SystemAccentColorDark3 #7E3B13 | Fläche tief #E3E5E1 | 6,56:1 | Verweis |
| hell | SystemAccentColorDark1 #A24C18 | Grund #EFF0ED | 5,12:1 | Verweis |
| hell | SystemAccentColorDark1 #A24C18 | Fläche #FFFFFF | 5,86:1 | Verweis |
| hell | SystemAccentColorDark1 #A24C18 | Fläche tief #E3E5E1 | 4,62:1 | Verweis |
| hell | Schrift von WinUI #FFFFFF | SystemAccentColorDark1 #A24C18 | 5,86:1 | Schrift auf Akzentfläche |
| hell | Fläche #FFFFFF | SystemAccentColorDark1 #A24C18 | 5,86:1 | Schrift auf Akzentfläche |
| hell | Schrift von WinUI #FFFFFF | SystemAccentColor #A24C18 | 5,86:1 | markierter Text |
| hell | Schrift von WinUI #FFFFFF | SystemAccentColorDark2 #A24C18 | 5,86:1 | Schrift auf AccentAA-Fläche |
| dunkel | SystemAccentColorLight3 #F2B558 | Grund #141715 | 9,90:1 | Verweis |
| dunkel | SystemAccentColorLight3 #F2B558 | Fläche #1C201D | 9,04:1 | Verweis |
| dunkel | SystemAccentColorLight3 #F2B558 | Fläche tief #262B27 | 7,90:1 | Verweis |
| dunkel | SystemAccentColorLight2 #DB7745 | Grund #141715 | 5,79:1 | Verweis |
| dunkel | SystemAccentColorLight2 #DB7745 | Fläche #1C201D | 5,28:1 | Verweis |
| dunkel | SystemAccentColorLight2 #DB7745 | Fläche tief #262B27 | 4,62:1 | Verweis |
| dunkel | Schrift von WinUI #000000 | SystemAccentColorLight2 #DB7745 | 6,73:1 | Schrift auf Akzentfläche |
| dunkel | Fläche #1C201D | SystemAccentColorLight2 #DB7745 | 5,28:1 | Schrift auf Akzentfläche |
| dunkel | Schrift von WinUI #FFFFFF | SystemAccentColor #A24C18 | 5,86:1 | markierter Text |
| dunkel | Schrift von WinUI #000000 | SystemAccentColorLight3 #F2B558 | 11,52:1 | Schrift auf AccentAA-Fläche |
| dunkel | Schrift von WinUI #000000 | SystemAccentColorLight1 #CF6028 | 5,35:1 | Schrift auf AccentAA-Fläche |
