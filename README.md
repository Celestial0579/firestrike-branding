# Firestrike-Branding

Farben, Schrift, Logos und Vorlagen für alle Firestrike-Oberflächen: Website, Anmeldeseite und Apps. Jedes Projekt nimmt seine Werte von hier, statt sie abzuschreiben. So sieht alles gleich aus, und eine Änderung erreicht alle.

![Farbtafel: alle Farbrollen im hellen und im dunklen Thema](docs/farbtafel.svg)

## Leitbild: Feuerstein auf Stahl

Feuerstein schlägt auf Stahl, ein Funke springt. Daher ein kühler Stahlgrund und ein einziger warmer Akzent. Kein Signalrot, kein zweiter Akzent, keine Verläufe. Kanten bleiben Kanten. Es gibt nur Systemschriften, damit beim Aufruf kein fremder Server kontaktiert wird. Die Regeln im Einzelnen stehen in [docs/nutzung.md](docs/nutzung.md).

## Inhalt

| Pfad | Inhalt |
|---|---|
| [`tokens/firestrike.json`](tokens/firestrike.json) | Quelle der Wahrheit: Farbrollen hell und dunkel, Kontrastpaare, Schrift, Form |
| [`exporte/`](exporte) | fertige Dateien je Plattform, erzeugt aus den Tokens |
| [`logos/`](logos) | Logo für helles und dunkles Thema, einfarbig, Symbol |
| [`kacheln/`](kacheln) | Vorlage für Kacheln von Diensten und Apps |
| [`docs/`](docs) | Nutzungsregeln, Kontrasttabelle, Farbtafel |
| [`werkzeuge/marke.py`](werkzeuge/marke.py) | erzeugt die Exporte und prüft alles |

## Exporte

| Plattform | Datei | Namen |
|---|---|---|
| Web (CSS) | `exporte/firestrike.css` | `--fs-grund`, `--fs-glut` … |
| Sass | `exporte/_firestrike.scss` | `$fs-glut`, `$fs-glut-dunkel`, Maps `$fs-hell` und `$fs-dunkel` |
| WordPress | `exporte/wordpress/firestrike.json`, `exporte/wordpress/farben.css` | Palette und Schriften für theme.json, dunkles Thema für style.css |
| Avalonia | `exporte/avalonia/Firestrike.axaml` | `Fs.Grund`, `Fs.Grund.Color` … |
| Anmeldeseite (PatternFly) | `exporte/anmeldeseite.css` | eigenes CSS der Anmeldeseite |

Im Web folgt Dunkel der Einstellung des Geräts. `data-theme="light"` oder `data-theme="dark"` am `<html>` legt das Thema fest. Jede Datei nennt im Kopf ihre Quelle und Version. Bitte kopierte Dateien nicht anpassen, sondern bei einer neuen Version ganz ersetzen.

Ein Export für WinUI 3 folgt. Er braucht eine eigene Akzentreihe und ein Wörterbuch für den Modus Hoher Kontrast.

## Ändern

1. `tokens/firestrike.json`, ein Logo oder eine Vorlage anpassen.
2. `python3 werkzeuge/marke.py erzeugen`
3. `python3 werkzeuge/marke.py pruefen`
4. Pull Request stellen.

Die Prüfung läuft auch bei jedem Push und Pull Request. Sie schlägt fehl, wenn

- ein Kontrastpaar in einem der beiden Themen unter seinem Mindestwert liegt (Text 4,5:1, Fokusrahmen 3:1, siehe [docs/kontraste.md](docs/kontraste.md)),
- eine erzeugte Datei nicht mehr zu den Tokens passt,
- ein SVG Skripte, Ereignis-Attribute, Verweise nach außen oder Farben außerhalb der Marke enthält oder `role="img"` und `aria-label` fehlen.

Python 3.10 oder neuer genügt, weitere Pakete braucht es nicht.

## Lizenz

Code, Tokens, Exporte und Doku stehen unter der [MIT-Lizenz](LICENSE). **Ausgenommen sind Logos, Wortmarke, Symbol und Kacheln** in `logos/` und `kacheln/`. Für sie gilt [MARKE.md](MARKE.md).

## Sicherheit

Schwachstellen bitte nicht als Issue melden, sondern so, wie es in [SECURITY.md](SECURITY.md) steht.
