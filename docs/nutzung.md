# Nutzung

So setzen Projekte die Marke ein. Die Werte stehen in [`tokens/firestrike.json`](../tokens/firestrike.json), die fertigen Dateien in [`exporte/`](../exporte), die gerechneten Kontraste in [kontraste.md](kontraste.md).

## Grundsätze

- **Ein Akzent.** Kühler Stahlgrund, ein warmer Akzent in zwei Stufen: Funke und Glut. Kein Signalrot, keine zweite Akzentfarbe, keine Verläufe, keine Schatten, kein Weichzeichner.
- **Rollen statt Farbtöne.** Im Code steht `glut`, `--fs-glut` oder `Fs.Glut`, nie `orange` und nie ein Hexwert. Die Rolle bleibt, der Ton darf sich ändern.
- **Kanten bleiben Kanten.** Radius 0 für Schaltflächen, Felder, Karten und Bilder. Nur Kacheln und App-Symbole sind abgerundet.
- **Nur Systemschriften.** Es werden keine Schriften ausgeliefert oder nachgeladen, damit beim Aufruf kein fremder Server kontaktiert wird.
- **Dunkel tauscht nur die Grundtöne.** Stahl, Funke und Glut bleiben als Rollen erhalten, damit die Marke erkennbar bleibt. Hell ist der Standard, Dunkel folgt der Einstellung des Geräts.

## Farbrollen

| Rolle | Wofür | Nie für |
|---|---|---|
| Grund | Seitengrund, unterste Ebene | |
| Fläche | Karten und Felder; Schrift auf Stahl und Glut | |
| Fläche tief | Quelltext, Tabellenköpfe, Hervorhebungen | |
| Linie | Trennlinien und Ränder | Bedeutung; nie die einzige Grenze eines Eingabefelds |
| Text | Fließtext | |
| Text leise | Datum, Bildunterschrift, Hilfetext | |
| Stahl | Schaltflächen, ruhige Akzentflächen, Verweis beim Überfahren | |
| Stahl tief | Überschriften und Wortmarke | Flächen: im dunklen Thema ist Stahl tief hell |
| Funke | Linien, Marker, Leisten an Zitaten und Quelltext | Text auf hellem Grund |
| Glut | Verweise, Schaltfläche beim Überfahren | |
| Fokus | Tastaturfokus, hell wie Glut, dunkel wie Funke | |

## Bausteine

- **Verweise im Fließtext:** Glut und unterstrichen (Abstand 0,18 em, Stärke 1 px), damit sie auch ohne Farbe erkennbar sind. Beim Überfahren Stahl.
- **Schaltflächen:** Fläche Stahl, Schrift in Fläche. Beim Überfahren und im Fokus Glut, Schrift weiter in Fläche. Im dunklen Thema ist Fläche dunkel, dort steht also dunkle Schrift auf Glut. Weiße Schrift wäre dort zu schwach.
- **Tastaturfokus:** 2 px durchgezogen in Fokus, 2 px Abstand. Nie entfernen.
- **Quelltext:** Mono auf Fläche tief, links eine 3 px breite Leiste in Funke.
- **Zitate:** links eine 3 px breite Leiste in Funke.
- **Trennlinie „Funkenschlag“:** 3 px hoch, höchstens 140 px breit, linksbündig, die ersten 40 % Funke, der Rest Glut.

## Schrift

| Rolle | Web | Windows und Avalonia |
|---|---|---|
| Serif: Überschriften, Seitentitel | Iowan Old Style, Palatino Linotype, Palatino, Book Antiqua, Georgia | Palatino Linotype, Book Antiqua, Georgia |
| Sans: Fließtext, Bedienung | system-ui, Segoe UI, Roboto, Helvetica Neue, Arial | Segoe UI Variable Text, Segoe UI |
| Mono: Quelltext | ui-monospace, SF Mono, Cascadia Mono, Menlo, Consolas | Cascadia Mono, Consolas |

Überschriften in Serif, Stärke 600, Zeilenhöhe 1,2, Farbe Stahl tief. Fließtext in Sans, Zeilenhöhe 1,65. Schriftgrößen, Abstände und Zeilenhöhen stehen mit ihren Namen je Plattform in [masse.md](masse.md).

## Logos

| Datei | Wofür |
|---|---|
| `logos/firestrike-logo-light.svg` | Logo für helles Thema und hellen Grund |
| `logos/firestrike-logo-dark.svg` | Logo für dunkles Thema und dunklen Grund |
| `logos/firestrike-logo-mono-light.svg` | einfarbig dunkel: heller Grund, Druck, Stempel |
| `logos/firestrike-logo-mono-dark.svg` | einfarbig hell: dunkler Grund, Fotos |
| `logos/firestrike-symbol.svg` | Symbol: Favicon, App-Symbol, Profilbild |

- Als Rasterbild liegt das Symbol unter `exporte/raster/`: `favicon.ico` und `favicon-32.png` für Browser, `site-icon-512.png` als Website-Icon in WordPress, `apple-touch-icon-180.png`, `profilbild-400.png`, `app.ico` für Windows-Programme und unter `msix/` die Kachelgrößen für MSIX-Pakete. Auf breiten Flächen (Wide310x150, SplashScreen) steht das Symbol mittig auf durchsichtigem Grund. Die Taskleistengrößen (`Square44x44Logo.targetsize-…`) gibt es zusätzlich als `…_altform-unplated`: Daran erkennt Windows, dass das Symbol ohne Platte gedacht ist, und zeigt es in Taskleiste und Startmenü in voller Größe statt auf einer Platte in der Hintergrundfarbe des Manifests.
- „light“ und „dark“ im Dateinamen meinen das Thema, für das die Datei gedacht ist. Eine Anwendung kann den Namen so aus dem Thema bilden, etwa `firestrike-logo-%(theme)s.svg`.
- Nicht verzerren, nicht drehen, nicht umfärben. Keine Schatten, Konturen oder Verläufe.
- Startwerte, Änderungen per Issue: Freiraum rundum mindestens ein Viertel der Logohöhe. Kleinste Größe 120 px Breite für das Logo, 16 px für das Symbol.
- Die Wortmarke steht als Pfade in den Logos und sieht darum überall gleich aus. Die Text-Fassungen zum Bearbeiten liegen unter `logos/quellen/`, siehe [logos/README.md](../logos/README.md#wortmarke-als-pfade).

## Kacheln

Kacheln sind die quadratischen Zeichen für Dienste und Anwendungen, etwa auf der Startseite nach der Anmeldung. Vorlage: [`kacheln/kachel-vorlage.svg`](../kacheln/kachel-vorlage.svg).

- 64 × 64, Ecken mit Radius 14, Fläche Stahl `#33414B`, in beiden Themen gleich.
- Zeichnung in `#E8EBE7`, Strichstärke 3, runde Enden und Ecken, keine großen Füllflächen.
- Genau ein Element in Funke `#E8A33D`.
- Eigene, einfache Zeichen: eine Form oder ein Buchstabe. Keine fremden Logos nachzeichnen.
- `role="img"` und ein `aria-label` mit dem Namen des Dienstes.
- Kacheln für einzelne Dienste gehören in das Projekt, das den Dienst betreibt, nicht in dieses Repo.
