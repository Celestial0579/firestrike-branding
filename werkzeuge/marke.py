#!/usr/bin/env python3
"""Firestrike-Marke: erzeugte Dateien schreiben und alles prüfen.

    python3 werkzeuge/marke.py erzeugen   schreibt alle erzeugten Dateien neu
    python3 werkzeuge/marke.py pruefen    prüft Tokens, Kontraste, erzeugte Dateien und SVGs

Nur Standardbibliothek, damit die Prüfung ohne Installation läuft (Python 3.10 oder neuer).
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

WURZEL = Path(__file__).resolve().parent.parent
TOKENS = "tokens/firestrike.json"
REPO = "https://github.com/Celestial0579/firestrike-branding"
THEMEN = ("hell", "dunkel")
HEX = re.compile(r"#[0-9A-F]{6}")
ROLLE = re.compile(r"[a-z]+(?:-[a-z]+)*")

# Einfarbige Logos: Ziel -> (farbige Quelle, Farbrolle, Thema)
EINFARBIG = {
    "logos/firestrike-logo-mono-light.svg": ("logos/firestrike-logo-light.svg", "text", "hell"),
    "logos/firestrike-logo-mono-dark.svg": ("logos/firestrike-logo-dark.svg", "text", "dunkel"),
}

# Was in keinem SVG der Marke stehen darf, weil es Code ausführt oder etwas nachlädt.
VERBOTEN = (
    (re.compile(r"<\s*script", re.I), "Skript"),
    (re.compile(r"\son[a-z]+\s*=", re.I), "Ereignis-Attribut"),
    (re.compile(r"<\s*foreignObject", re.I), "foreignObject"),
    (re.compile(r"<!(?:DOCTYPE|ENTITY)", re.I), "DOCTYPE oder ENTITY"),
    (re.compile(r"\bhref\s*=\s*[\"'](?!#)", re.I), "Verweis nach außen"),
    (re.compile(r"url\(\s*[\"']?(?!#)", re.I), "url() nach außen"),
    (re.compile(r"@import", re.I), "@import"),
)
FARBE = re.compile(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b")
BENANNT = re.compile(r"\b(?:fill|stroke|stop-color|color)\s*=\s*[\"'](?!#|none\b|currentColor\b)([^\"']+)", re.I)


# --- Tokens und Rechnen -------------------------------------------------------


def laden() -> dict:
    """Liest die Tokens, prüft ihren Aufbau und löst Verweise wie "=glut" auf."""
    daten = json.loads((WURZEL / TOKENS).read_text(encoding="utf-8"))
    farben = daten["farben"]
    rollen = {f["rolle"]: f for f in farben}
    fehler = []
    if len(rollen) != len(farben):
        fehler.append("eine Rolle steht doppelt")
    for f in farben:
        if not ROLLE.fullmatch(f["rolle"]):
            fehler.append(f"Rolle {f['rolle']!r}: nur a-z und Bindestrich")
        if "--" in f["zweck"] or "*/" in f["zweck"]:
            fehler.append(f"Rolle {f['rolle']}: zweck landet in Kommentaren, darum weder -- noch */")
        for t in THEMEN:
            w = f[t]
            if w.startswith("="):
                ziel = rollen.get(w[1:])
                if ziel is None or ziel[t].startswith("="):
                    fehler.append(f"{f['rolle']}.{t} = {w}: Ziel ist keine Rolle mit eigenem Wert")
            elif not HEX.fullmatch(w):
                fehler.append(f"{f['rolle']}.{t} = {w!r}: erwartet #RRGGBB in Großbuchstaben")
    for p in daten["kontrastpaare"] + daten["schmuckpaare"]:
        hinten = p["hinten"] if isinstance(p["hinten"], list) else [p["hinten"]]
        for r in (p["vorne"], *hinten):
            if r not in rollen:
                fehler.append(f"Paar mit unbekannter Rolle {r!r}")
    if fehler:
        raise SystemExit(f"{TOKENS}:\n  " + "\n  ".join(fehler))
    daten["wert"] = {
        t: {f["rolle"]: rollen[f[t][1:]][t] if f[t].startswith("=") else f[t] for f in farben}
        for t in THEMEN
    }
    return daten


def leuchtdichte(farbe: str) -> float:
    """Relative Leuchtdichte nach WCAG 2.2."""
    kanaele = [int(farbe[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in kanaele]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def kontrast(a: str, b: str) -> float:
    oben, unten = sorted((leuchtdichte(a), leuchtdichte(b)), reverse=True)
    return (oben + 0.05) / (unten + 0.05)


def zahl(x: float) -> str:
    """Zwei Stellen mit Komma, abgerundet: 4,499 erscheint als 4,49, nie als 4,50."""
    return f"{math.floor(x * 100) / 100:.2f}".replace(".", ",")


def grenze(x: float) -> str:
    return f"{x:g}".replace(".", ",")


def paare(daten: dict):
    for p in daten["kontrastpaare"]:
        for hinten in p["hinten"]:
            yield p["vorne"], hinten, p["mindestens"], p["fuer"]


def kopf(daten: dict, quelle: str = TOKENS) -> list[str]:
    return [
        f"Firestrike: {daten['leitbild']}.",
        f"Erzeugt aus {quelle} (Version {daten['version']}) von werkzeuge/marke.py.",
        f"Nicht von Hand ändern, sondern in {REPO}",
    ]


def pascal(rolle: str) -> str:
    return "".join(teil.capitalize() for teil in rolle.split("-"))


def ohne_px(wert: str) -> str:
    return wert.removesuffix("px")


# --- CSS und Sass -------------------------------------------------------------


def css_wert(f: dict, t: str) -> str:
    w = f[t]
    return f"var(--fs-{w[1:]})" if w.startswith("=") else w


def css_farben(daten: dict, t: str, einzug: str, mit_zweck: bool = False) -> list[str]:
    zeilen = []
    for f in daten["farben"]:
        if mit_zweck:
            zeilen.append(f"{einzug}/* {f['zweck']} */")
        zeilen.append(f"{einzug}--fs-{f['rolle']}: {css_wert(f, t)};")
    return zeilen


def css_form_schrift(daten: dict, einzug: str) -> list[str]:
    form = daten["form"]
    zeilen = [
        f"{einzug}--fs-radius: {form['radius']};",
        f"{einzug}--fs-fokus-staerke: {form['fokus-staerke']};",
        f"{einzug}--fs-fokus-abstand: {form['fokus-abstand']};",
    ]
    return zeilen + [f"{einzug}--fs-{k}: {v['css']};" for k, v in daten["schrift"].items()]


def css(daten: dict) -> str:
    z = [
        "/*", *(f" * {s}" for s in kopf(daten)), " *",
        " * Hell ist der Standard, Dunkel folgt dem Gerät (prefers-color-scheme).",
        ' * data-theme="light" oder data-theme="dark" am <html> legt das Thema fest.',
        " */",
        ":root {", "  color-scheme: light;",
        *css_farben(daten, "hell", "  ", mit_zweck=True),
        *css_form_schrift(daten, "  "),
        "}", "",
        "@media (prefers-color-scheme: dark) {",
        '  :root:not([data-theme="light"]) {', "    color-scheme: dark;",
        *css_farben(daten, "dunkel", "    "),
        "  }", "}", "",
        ':root[data-theme="dark"] {', "  color-scheme: dark;",
        *css_farben(daten, "dunkel", "  "),
        "}",
    ]
    return "\n".join(z) + "\n"


def scss(daten: dict) -> str:
    form, wert = daten["form"], daten["wert"]
    z = [*(f"// {s}" for s in kopf(daten)), "//",
         "// Farben heißen nach ihrer Rolle, nie nach dem Farbton.", "", "// --- hell ---", ""]
    for f in daten["farben"]:
        z += [f"/// {f['zweck']}", f"$fs-{f['rolle']}: {wert['hell'][f['rolle']].lower()};"]
    z += ["", "// --- dunkel ---", ""]
    z += [f"$fs-{f['rolle']}-dunkel: {wert['dunkel'][f['rolle']].lower()};" for f in daten["farben"]]
    z += ["", "// --- als Maps, etwa für @each ---", "", "$fs-hell: ("]
    z += [f"  {f['rolle']}: $fs-{f['rolle']}," for f in daten["farben"]]
    z += [");", "$fs-dunkel: ("]
    z += [f"  {f['rolle']}: $fs-{f['rolle']}-dunkel," for f in daten["farben"]]
    z += [");", "", "// --- Form und Schrift ---", "",
          "/// Kanten bleiben Kanten.", f"$fs-radius: {form['radius']};",
          "/// Tastaturfokus: durchgezogen, mit Abstand, in der Rolle Fokus.",
          f"$fs-fokus-staerke: {form['fokus-staerke']};", f"$fs-fokus-abstand: {form['fokus-abstand']};",
          "/// Nur Systemschriften, es wird nichts ausgeliefert."]
    z += [f"$fs-{k}: {v['css']};" for k, v in daten["schrift"].items()]
    return "\n".join(z) + "\n"


# --- WordPress ----------------------------------------------------------------


def wordpress(daten: dict) -> tuple[str, str]:
    """theme.json-Ausschnitt mit Palette und Schriften, dazu das CSS für style.css."""
    palette = [f for f in daten["farben"] if not f["hell"].startswith("=")]
    in_palette = {f["rolle"] for f in palette}

    def name(rolle: str) -> str:
        return f"--wp--preset--color--{rolle}" if rolle in in_palette else f"--fs-{rolle}"

    def zeile(f: dict, t: str, einzug: str) -> str:
        w = f[t]
        wert = f"var({name(w[1:])})" if w.startswith("=") else w
        return f"{einzug}{name(f['rolle'])}: {wert};"

    theme = {
        "$schema": "https://schemas.wp.org/trunk/theme.json",
        "version": 3,
        "settings": {
            "color": {
                "defaultPalette": False,
                "defaultGradients": False,
                "custom": False,
                "palette": [{"slug": f["rolle"], "name": f["name"], "color": f["hell"]} for f in palette],
            },
            "typography": {
                "fontFamilies": [
                    {"slug": k, "name": v["name"], "fontFamily": v["css"]} for k, v in daten["schrift"].items()
                ],
            },
        },
    }
    z = [
        "/*", *(f" * {s}" for s in kopf(daten)), " *",
        " * Für style.css des WordPress-Themes. Die hellen Farben stehen als Palette",
        " * in theme.json (firestrike.json hier daneben). Hier stehen die",
        " * abgeleiteten Rollen und das dunkle Thema.",
        " */",
        ":root {", *(zeile(f, "hell", "\t") for f in daten["farben"] if f["rolle"] not in in_palette), "}", "",
        "@media (prefers-color-scheme: dark) {", "\t:root {",
        *(zeile(f, "dunkel", "\t\t") for f in daten["farben"]),
        "\t}", "}",
    ]
    return json.dumps(theme, ensure_ascii=False, indent="\t") + "\n", "\n".join(z) + "\n"


# --- Avalonia -----------------------------------------------------------------


def avalonia(daten: dict) -> str:
    form, wert = daten["form"], daten["wert"]
    z = ["<!--", *(f"  {s}" for s in kopf(daten)),
         "  Farben heißen nach ihrer Rolle (Fs.Grund, Fs.Text …), nie nach dem Farbton.",
         "-->",
         '<ResourceDictionary xmlns="https://github.com/avaloniaui"',
         '                    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">',
         "  <ResourceDictionary.ThemeDictionaries>"]
    for t, schluessel in (("hell", "Light"), ("dunkel", "Dark")):
        z.append(f'    <ResourceDictionary x:Key="{schluessel}">')
        for f in daten["farben"]:
            n, w = pascal(f["rolle"]), wert[t][f["rolle"]].lower()
            z += [f"      <!-- {f['zweck']} -->",
                  f'      <Color x:Key="Fs.{n}.Color">{w}</Color>',
                  f'      <SolidColorBrush x:Key="Fs.{n}" Color="{w}" />']
        z.append("    </ResourceDictionary>")
    z += ["  </ResourceDictionary.ThemeDictionaries>", "",
          "  <!-- Kanten bleiben Kanten: die Radien von Fluent auf 0. -->",
          f'  <CornerRadius x:Key="ControlCornerRadius">{form["radius"]}</CornerRadius>',
          f'  <CornerRadius x:Key="OverlayCornerRadius">{form["radius"]}</CornerRadius>',
          "  <!-- Tastaturfokus: durchgezogen, mit Abstand. -->",
          f'  <Thickness x:Key="Fs.FocusThickness">{ohne_px(form["fokus-staerke"])}</Thickness>',
          f'  <Thickness x:Key="Fs.FocusOffset">{ohne_px(form["fokus-abstand"])}</Thickness>',
          "  <!-- Nur Systemschriften, es wird nichts ausgeliefert. -->"]
    z += [f'  <FontFamily x:Key="Fs.Font.{pascal(k)}">{v["xaml"]}</FontFamily>' for k, v in daten["schrift"].items()]
    z.append("</ResourceDictionary>")
    return "\n".join(z) + "\n"


# --- Anmeldeseite, Logos, Doku --------------------------------------------------


def anmeldeseite(daten: dict) -> str:
    quelle = "vorlagen/anmeldeseite.css"
    vorlage = (WURZEL / quelle).read_text(encoding="utf-8")
    if vorlage.count("/* @variablen */") != 1:
        raise SystemExit(f"{quelle}: der Platzhalter /* @variablen */ muss genau einmal vorkommen")
    block = [":root {", *css_farben(daten, "hell", "  "), *css_form_schrift(daten, "  "), "}",
             "@media (prefers-color-scheme: dark) {", "  :root {", *css_farben(daten, "dunkel", "    "), "  }", "}"]
    vorne = ["/*", *(f" * {s}" for s in kopf(daten, f"{TOKENS} und {quelle}")), " */"]
    return "\n".join(vorne) + "\n" + vorlage.replace("/* @variablen */", "\n".join(block))


def einfarbig(daten: dict, quelle: str, rolle: str, thema: str) -> str:
    text = (WURZEL / quelle).read_text(encoding="utf-8")
    return FARBE.sub(daten["wert"][thema][rolle], text)


def farbtafel(daten: dict) -> str:
    farben = daten["farben"]
    breite, zeile, oben = 320, 34, 56
    hoehe = oben + len(farben) * zeile + 12
    sans = "ui-sans-serif, system-ui, 'Segoe UI', Roboto, Arial, sans-serif"
    mono = "ui-monospace, 'Cascadia Mono', Consolas, monospace"
    z = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {2 * breite} {hoehe}" width="{2 * breite}" '
         f'height="{hoehe}" role="img" aria-label="Firestrike-Farbtafel, hell und dunkel">']
    for i, (t, titel) in enumerate((("hell", "Hell"), ("dunkel", "Dunkel"))):
        w, x = daten["wert"][t], i * breite
        z.append(f'<rect x="{x}" y="0" width="{breite}" height="{hoehe}" fill="{w["grund"]}"/>')
        z.append(f'<text x="{x + 20}" y="34" font-family="{sans}" font-size="17" font-weight="700" '
                 f'fill="{w["stahl-tief"]}">{titel}</text>')
        for j, eintrag in enumerate(farben):
            y, farbe = oben + j * zeile, w[eintrag["rolle"]]
            z.append(f'<rect x="{x + 20}" y="{y}" width="26" height="26" fill="{farbe}" stroke="{w["linie"]}"/>')
            z.append(f'<text x="{x + 58}" y="{y + 18}" font-family="{sans}" font-size="14" '
                     f'fill="{w["text"]}">{escape(eintrag["name"])}</text>')
            z.append(f'<text x="{x + breite - 20}" y="{y + 18}" font-family="{mono}" font-size="13" '
                     f'fill="{w["text-leise"]}" text-anchor="end">{farbe}</text>')
    z.append("</svg>")
    return "\n".join(z) + "\n"


def kontraste_md(daten: dict) -> str:
    name = {f["rolle"]: f["name"] for f in daten["farben"]}
    wert = daten["wert"]

    def k(vorne: str, hinten: str, t: str) -> str:
        return zahl(kontrast(wert[t][vorne], wert[t][hinten])) + ":1"

    z = ["# Kontraste", "",
         "Erzeugt von `werkzeuge/marke.py` aus `tokens/firestrike.json`, nicht von Hand ändern.",
         "Gerechnet nach WCAG 2.2 aus der relativen Leuchtdichte, abgerundet auf zwei Stellen.",
         "Die Prüfung schlägt fehl, sobald ein Paar in einem der beiden Themen unter seinem Mindestwert liegt.", "",
         "| Vorne | Hinten | Hell | Dunkel | Mindestens | Wofür |",
         "|---|---|---:|---:|---:|---|"]
    for vorne, hinten, mindestens, fuer in paare(daten):
        z.append(f"| {name[vorne]} | {name[hinten]} | {k(vorne, hinten, 'hell')} | {k(vorne, hinten, 'dunkel')} "
                 f"| {grenze(mindestens)}:1 | {fuer} |")
    z += ["", "## Nur Schmuck", "",
          "Diese Paare liegen mindestens in einem Thema unter 4,5:1. Sie tragen darum nie Text oder Bedeutung.", "",
          "| Vorne | Hinten | Hell | Dunkel | Hinweis |", "|---|---|---:|---:|---|"]
    for p in daten["schmuckpaare"]:
        v, h = p["vorne"], p["hinten"]
        z.append(f"| {name[v]} | {name[h]} | {k(v, h, 'hell')} | {k(v, h, 'dunkel')} | {p['hinweis']} |")
    return "\n".join(z) + "\n"


def erzeugte(daten: dict) -> dict[str, str]:
    wp_json, wp_css = wordpress(daten)
    dateien = {
        "exporte/firestrike.css": css(daten),
        "exporte/_firestrike.scss": scss(daten),
        "exporte/wordpress/firestrike.json": wp_json,
        "exporte/wordpress/farben.css": wp_css,
        "exporte/avalonia/Firestrike.axaml": avalonia(daten),
        "exporte/anmeldeseite.css": anmeldeseite(daten),
        "docs/farbtafel.svg": farbtafel(daten),
        "docs/kontraste.md": kontraste_md(daten),
    }
    for ziel, (quelle, rolle, thema) in EINFARBIG.items():
        dateien[ziel] = einfarbig(daten, quelle, rolle, thema)
    return dateien


# --- Befehle --------------------------------------------------------------------


def svg_pruefen(pfad: Path, erlaubt: set[str]) -> list[str]:
    rel = pfad.relative_to(WURZEL).as_posix()
    text = pfad.read_text(encoding="utf-8")
    fehler = [f"{rel}: {was}" for muster, was in VERBOTEN if muster.search(text)]
    for farbe in sorted(set(FARBE.findall(text))):
        voll = farbe.upper() if len(farbe) == 7 else "#" + "".join(c * 2 for c in farbe[1:].upper())
        if voll not in erlaubt:
            fehler.append(f"{rel}: Farbe {farbe} gehört nicht zur Marke")
    fehler += [f"{rel}: Farbe {w!r} bitte als #RRGGBB aus der Marke" for w in sorted(set(BENANNT.findall(text)))]
    wurzel = re.search(r"<svg\b[^>]*>", text)
    if not wurzel or 'role="img"' not in wurzel.group(0) or not re.search(r'aria-label="[^"]+"', wurzel.group(0)):
        fehler.append(f'{rel}: <svg> braucht role="img" und ein aria-label')
    return fehler


def erzeugen() -> int:
    daten = laden()
    for pfad, inhalt in erzeugte(daten).items():
        ziel = WURZEL / pfad
        if ziel.is_file() and ziel.read_text(encoding="utf-8") == inhalt:
            continue
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding="utf-8", newline="\n")
        print(f"geschrieben: {pfad}")
    return 0


def pruefen() -> int:
    daten = laden()
    fehler: list[str] = []
    if abs(kontrast("#FFFFFF", "#000000") - 21) > 1e-9:
        fehler.append("Kontrastrechnung: Weiß auf Schwarz ergibt nicht 21:1")
    anzahl = 0
    for vorne, hinten, mindestens, fuer in paare(daten):
        for t in THEMEN:
            anzahl += 1
            k = kontrast(daten["wert"][t][vorne], daten["wert"][t][hinten])
            if k < mindestens:
                fehler.append(f"Kontrast {t}: {vorne} auf {hinten} = {zahl(k)}:1, "
                              f"braucht {grenze(mindestens)}:1 ({fuer})")
    dateien = erzeugte(daten)
    for pfad, inhalt in dateien.items():
        ziel = WURZEL / pfad
        if not ziel.is_file():
            fehler.append(f"fehlt: {pfad}, bitte python3 werkzeuge/marke.py erzeugen")
        elif ziel.read_text(encoding="utf-8") != inhalt:
            fehler.append(f"veraltet: {pfad}, bitte python3 werkzeuge/marke.py erzeugen")
    erlaubt = {w for t in THEMEN for w in daten["wert"][t].values()}
    svgs = sorted(p for p in WURZEL.rglob("*.svg") if ".git" not in p.relative_to(WURZEL).parts)
    for svg in svgs:
        fehler += svg_pruefen(svg, erlaubt)
    if fehler:
        print("Prüfung fehlgeschlagen:")
        print("\n".join(f"  - {f}" for f in fehler))
        return 1
    print(f"Prüfung bestanden: {anzahl} Kontraste, {len(dateien)} erzeugte Dateien, {len(svgs)} SVGs.")
    return 0


def main(argv: list[str]) -> int:
    befehle = {"erzeugen": erzeugen, "pruefen": pruefen}
    if len(argv) != 2 or argv[1] not in befehle:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    return befehle[argv[1]]()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
