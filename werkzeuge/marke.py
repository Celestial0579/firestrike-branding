#!/usr/bin/env python3
"""Firestrike-Marke: erzeugte Dateien schreiben, alles prüfen, Kopien abgleichen.

    python3 werkzeuge/marke.py erzeugen
        schreibt alle erzeugten Dateien neu
    python3 werkzeuge/marke.py pruefen
        prüft Tokens, Kontraste, erzeugte Dateien, SVGs und den Abgleich
    python3 werkzeuge/marke.py abgleichen DATEI [--format FORMAT] [--streng]
        vergleicht die Kopie eines Projekts mit den Tokens. FORMAT ist css,
        scss, avalonia oder wordpress, ohne --format gilt die Endung der Datei.
        Exit-Code 0: passt, 1: Abweichung, 2: Aufruf oder Datei unbrauchbar.
    python3 werkzeuge/marke.py raster
        erzeugt die Rasterbilder unter exporte/raster neu; braucht rsvg-convert
        (Paket librsvg2-bin), sonst nur die Standardbibliothek
    python3 werkzeuge/marke.py wortmarke SCHRIFT.ttf
        setzt die Wortmarke aus logos/quellen/*-text.svg als Pfade in die Logos
        unter logos/; SCHRIFT ist Liberation Sans Bold (SIL Open Font License 1.1)

Nur Standardbibliothek und kein Netzzugriff, damit alles ohne Installation läuft
(Python 3.10 oder neuer).
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from xml.parsers import expat
from xml.sax.saxutils import escape

WURZEL = Path(__file__).resolve().parent.parent
TOKENS = "tokens/firestrike.json"
REPO = "https://github.com/Celestial0579/firestrike-branding"
THEMEN = ("hell", "dunkel")
HEX = re.compile(r"#[0-9A-F]{6}")
ROLLE = re.compile(r"[a-z]+(?:-[a-z]+)*")
LAENGE = re.compile(r"(\d+(?:\.\d+)?)(px|rem)")
ZAHL = re.compile(r"\d+(?:\.\d+)?")

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

# Schriftstärken von CSS und XAML, damit 600 und SemiBold dasselbe sind.
STAERKEN = {
    "thin": 100, "extralight": 200, "ultralight": 200, "light": 300, "semilight": 350,
    "normal": 400, "regular": 400, "medium": 500, "semibold": 600, "demibold": 600,
    "bold": 700, "extrabold": 800, "ultrabold": 800, "black": 900, "heavy": 900,
    "extrablack": 950, "ultrablack": 950,
}
XAML_STAERKE = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Normal", 500: "Medium",
                600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}


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
    fehler += masse_pruefen(daten)
    if fehler:
        raise SystemExit(f"{TOKENS}:\n  " + "\n  ".join(fehler))
    daten["wert"] = {
        t: {f["rolle"]: rollen[f[t][1:]][t] if f[t].startswith("=") else f[t] for f in farben}
        for t in THEMEN
    }
    return daten


def masse_pruefen(daten: dict) -> list[str]:
    """Prüft Schriftgrößen, Abstände und Satz auf Form und Reihenfolge."""
    fehler = []
    groessen = daten["groessen"]
    fluessig = groessen["fluessig"]
    if not all(LAENGE.fullmatch(fluessig[k]) for k in ("von", "bis")):
        fehler.append("groessen.fluessig: von und bis brauchen px oder rem")
    elif rem(fluessig["von"]) >= rem(fluessig["bis"]):
        fehler.append("groessen.fluessig: von muss kleiner sein als bis")
    gesehen: set[str] = set()
    for s in groessen["stufen"]:
        r = s["rolle"]
        if not ROLLE.fullmatch(r) or r in gesehen or r in {f["rolle"] for f in daten["farben"]}:
            fehler.append(f"Größe {r!r}: Rolle aus a-z und Bindestrich, nur einmal und nicht wie eine Farbe")
        gesehen.add(r)
        if not re.fullmatch(r"[a-z0-9-]+", s["wordpress"]):
            fehler.append(f"Größe {r}: Slug {s['wordpress']!r} nur aus a-z, 0-9 und Bindestrich")
        if not all(LAENGE.fullmatch(s[k]) for k in ("wert", "min", "max") if k in s):
            fehler.append(f"Größe {r}: wert, min und max brauchen px oder rem")
        elif ("min" in s) != ("max" in s):
            fehler.append(f"Größe {r}: min und max nur gemeinsam")
        elif "min" in s:
            mini, wert, maxi = rem(s["min"]), rem(s["wert"]), rem(s["max"])
            if not (mini < maxi and mini <= wert <= maxi):
                fehler.append(f"Größe {r}: es muss min < max gelten und wert dazwischen liegen")
    stufen = [a["stufe"] for a in daten["abstaende"]]
    if not all(re.fullmatch(r"[1-9][0-9]*", s) for s in stufen) or len(set(stufen)) != len(stufen):
        fehler.append("abstaende: jede Stufe eine Zahl, jede nur einmal")
    if not all(LAENGE.fullmatch(a["wert"]) for a in daten["abstaende"]):
        fehler.append("abstaende: Werte brauchen px oder rem")
    else:
        werte = [rem(a["wert"]) for a in daten["abstaende"]]
        if werte != sorted(set(werte)):
            fehler.append("abstaende: Werte müssen mit der Stufe wachsen")
    satz = daten["satz"]
    for k in ("zeilenhoehe-text", "zeilenhoehe-ueberschrift"):
        if not ZAHL.fullmatch(satz[k]):
            fehler.append(f"satz.{k}: erwartet eine Zahl ohne Einheit")
    if satz["staerke-ueberschrift"] not in {str(z) for z in XAML_STAERKE}:
        fehler.append("satz.staerke-ueberschrift: erwartet 100, 200 … 900")
    return fehler


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


def rem(wert: str) -> Decimal:
    """Länge in rem, 1rem = 16px."""
    betrag, einheit = LAENGE.fullmatch(wert).groups()
    return Decimal(betrag) / 16 if einheit == "px" else Decimal(betrag)


def dezimal(d: Decimal) -> str:
    """Zahl ohne überflüssige Nullen: 1.30 wird 1.3, 16.0 wird 16."""
    return format(d.normalize(), "f")


def px(wert: str) -> str:
    """Länge in Pixeln ohne Einheit, für Apps."""
    return dezimal(rem(wert) * 16)


def php_runden(d: Decimal, stellen: int = 3) -> Decimal:
    """Rundet wie PHPs round(): bei 5 von der Null weg."""
    return d.quantize(Decimal(1).scaleb(-stellen), rounding=ROUND_HALF_UP)


def fliessend(daten: dict, stufe: dict) -> str:
    """clamp() einer fließenden Größe, gerechnet wie WordPress (wp_get_computed_fluid_typography_value)."""
    von, bis = daten["groessen"]["fluessig"]["von"], daten["groessen"]["fluessig"]["bis"]
    mini, maxi = stufe["min"], stufe["max"]
    einheit = LAENGE.fullmatch(mini).group(2)

    def wert(x: str) -> Decimal:
        return php_runden(rem(x) if einheit == "rem" else rem(x) * 16)

    breite_min, breite_max = wert(von), wert(bis)
    versatz = php_runden(breite_min / 100)
    faktor = php_runden(100 * (wert(maxi) - wert(mini)) / (breite_max - breite_min)) or Decimal(1)
    return (f"clamp({mini}, {dezimal(php_runden(rem(mini)))}rem + "
            f"((1vw - {dezimal(versatz)}{einheit}) * {dezimal(faktor)}), {maxi})")


def xaml_satz(schluessel: str) -> str:
    """zeilenhoehe-text -> Fs.Zeilenhoehe.Text"""
    vorne, hinten = schluessel.split("-", 1)
    return f"Fs.{pascal(vorne)}.{pascal(hinten)}"


def css_groesse(daten: dict, stufe: dict) -> str:
    return fliessend(daten, stufe) if "min" in stufe else stufe["wert"]


def wp_groesse(wert: str, mini: str | None, maxi: str | None) -> str:
    """Größe so, wie theme.json sie beschreibt, als ein vergleichbarer Text."""
    if mini is None and maxi is None:
        return wert
    return f"{wert}, fließend {mini or '?'} bis {maxi or '?'}"


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
    zeilen += [f"{einzug}--fs-{k}: {v['css']};" for k, v in daten["schrift"].items()]
    zeilen += [f"{einzug}--fs-groesse-{s['rolle']}: {css_groesse(daten, s)};" for s in daten["groessen"]["stufen"]]
    zeilen += [f"{einzug}--fs-abstand-{a['stufe']}: {a['wert']};" for a in daten["abstaende"]]
    return zeilen + [f"{einzug}--fs-{k}: {v};" for k, v in daten["satz"].items()]


def css(daten: dict) -> str:
    z = [
        "/*", *(f" * {s}" for s in kopf(daten)), " *",
        " * Hell ist der Standard, Dunkel folgt dem Gerät (prefers-color-scheme).",
        ' * data-theme="light" oder data-theme="dark" am <html> legt das Thema fest.',
        " * Fließende Schriftgrößen wachsen mit der Fensterbreite, siehe docs/masse.md.",
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
    form, wert, satz = daten["form"], daten["wert"], daten["satz"]
    stufen, abstaende = daten["groessen"]["stufen"], daten["abstaende"]
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
    z += ["", "// --- Größen, Abstände und Satz ---", "",
          "/// Schriftgrößen; die fließenden wachsen mit der Fensterbreite (docs/masse.md)."]
    z += [f"$fs-groesse-{s['rolle']}: {css_groesse(daten, s)};" for s in stufen]
    z += ["/// Abstände, Stufen wie im Website-Theme."]
    z += [f"$fs-abstand-{a['stufe']}: {a['wert']};" for a in abstaende]
    z += ["/// Zeilenhöhen und Stärke der Überschriften."]
    z += [f"$fs-{k}: {v};" for k, v in satz.items()]
    z += ["$fs-groessen: ("]
    z += [f"  {s['rolle']}: $fs-groesse-{s['rolle']}," for s in stufen]
    z += [");", "$fs-abstaende: ("]
    z += [f"  {a['stufe']}: $fs-abstand-{a['stufe']}," for a in abstaende]
    z.append(");")
    return "\n".join(z) + "\n"


# --- WordPress ----------------------------------------------------------------


def wordpress(daten: dict) -> tuple[str, str]:
    """theme.json-Ausschnitt mit Palette, Schriften, Größen und Abständen, dazu das CSS für style.css."""
    palette = [f for f in daten["farben"] if not f["hell"].startswith("=")]
    in_palette = {f["rolle"] for f in palette}
    fluessig = daten["groessen"]["fluessig"]
    satz = daten["satz"]

    def name(rolle: str) -> str:
        return f"--wp--preset--color--{rolle}" if rolle in in_palette else f"--fs-{rolle}"

    def zeile(f: dict, t: str, einzug: str) -> str:
        w = f[t]
        wert = f"var({name(w[1:])})" if w.startswith("=") else w
        return f"{einzug}{name(f['rolle'])}: {wert};"

    def groesse(s: dict) -> dict:
        eintrag = {"slug": s["wordpress"], "name": s["name"], "size": s["wert"]}
        if "min" in s:
            eintrag["fluid"] = {"min": s["min"], "max": s["max"]}
        return eintrag

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
                "defaultFontSizes": False,
                "fluid": {"minViewportWidth": fluessig["von"], "maxViewportWidth": fluessig["bis"]},
                "fontFamilies": [
                    {"slug": k, "name": v["name"], "fontFamily": v["css"]} for k, v in daten["schrift"].items()
                ],
                "fontSizes": [groesse(s) for s in daten["groessen"]["stufen"]],
            },
            "spacing": {
                "defaultSpacingSizes": False,
                "spacingSizes": [
                    {"slug": a["stufe"], "name": str(i), "size": a["wert"]}
                    for i, a in enumerate(daten["abstaende"], start=1)
                ],
            },
        },
        "styles": {
            "typography": {"lineHeight": satz["zeilenhoehe-text"]},
            "elements": {
                "heading": {
                    "typography": {
                        "fontWeight": satz["staerke-ueberschrift"],
                        "lineHeight": satz["zeilenhoehe-ueberschrift"],
                    },
                },
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
    form, wert, satz = daten["form"], daten["wert"], daten["satz"]
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
    z += ["  <!-- Schriftgrößen und Abstände in Pixeln (1rem = 16 px). Apps nehmen die feste Größe. -->"]
    z += [f'  <x:Double x:Key="Fs.Groesse.{pascal(s["rolle"])}">{px(s["wert"])}</x:Double>'
          for s in daten["groessen"]["stufen"]]
    z += [f'  <x:Double x:Key="Fs.Abstand.{a["stufe"]}">{px(a["wert"])}</x:Double>' for a in daten["abstaende"]]
    z.append("  <!-- Zeilenhöhen als Faktor der Schriftgröße, Stärke der Überschriften. -->")
    for k, v in satz.items():
        if k.startswith("staerke-"):
            z.append(f'  <FontWeight x:Key="{xaml_satz(k)}">{XAML_STAERKE[int(v)]}</FontWeight>')
        else:
            z.append(f'  <x:Double x:Key="{xaml_satz(k)}">{v}</x:Double>')
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


def masse_md(daten: dict) -> str:
    fluessig, satz = daten["groessen"]["fluessig"], daten["satz"]

    def komma(wert: str) -> str:
        return wert.replace(".", ",")

    z = ["# Größen und Abstände", "",
         "Erzeugt von `werkzeuge/marke.py` aus `tokens/firestrike.json`, nicht von Hand ändern.", "",
         "## Schriftgrößen", "",
         f"Eine fließende Größe wächst zwischen {komma(fluessig['von'])} und {komma(fluessig['bis'])} "
         "Fensterbreite gleichmäßig von „ab“ auf „bis“. So rechnet auch WordPress. "
         "Apps nehmen die feste Größe in Pixeln (1rem = 16 px).", "",
         "| Rolle | Fest | Fließend ab | bis | Apps (px) | CSS | WordPress |",
         "|---|---:|---:|---:|---:|---|---|"]
    for s in daten["groessen"]["stufen"]:
        z.append(f"| {s['name']} | {komma(s['wert'])} | {komma(s.get('min', '–'))} | {komma(s.get('max', '–'))} "
                 f"| {komma(px(s['wert']))} | `--fs-groesse-{s['rolle']}` | `{s['wordpress']}` |")
    z += ["", "## Abstände", "",
          "| Stufe | Wert | Apps (px) | CSS | WordPress |", "|---|---:|---:|---|---|"]
    for a in daten["abstaende"]:
        z.append(f"| {a['stufe']} | {komma(a['wert'])} | {komma(px(a['wert']))} "
                 f"| `--fs-abstand-{a['stufe']}` | `{a['stufe']}` |")
    z += ["", "## Satz", "",
          "| Wofür | Wert | CSS |", "|---|---:|---|",
          f"| Zeilenhöhe im Fließtext | {komma(satz['zeilenhoehe-text'])} | `--fs-zeilenhoehe-text` |",
          f"| Zeilenhöhe der Überschriften | {komma(satz['zeilenhoehe-ueberschrift'])} "
          "| `--fs-zeilenhoehe-ueberschrift` |",
          f"| Stärke der Überschriften | {satz['staerke-ueberschrift']} | `--fs-staerke-ueberschrift` |"]
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
        "docs/masse.md": masse_md(daten),
    }
    for ziel, (quelle, rolle, thema) in EINFARBIG.items():
        dateien[ziel] = einfarbig(daten, quelle, rolle, thema)
    return dateien


# --- Abgleich -------------------------------------------------------------------

ALTE_GLUT = re.compile(r"#(?:AB5019|D9713C)\b", re.I)
ENDUNGEN = {".css": "css", ".scss": "scss", ".axaml": "avalonia", ".json": "wordpress"}
FORMATE = ("css", "scss", "avalonia", "wordpress")
XAML_NS = "http://schemas.microsoft.com/winfx/2006/xaml"
GROESSTE_DATEI = 2 * 1024 * 1024


class Unbrauchbar(Exception):
    """Aufruf oder Datei lassen keinen Abgleich zu (Exit-Code 2)."""


@dataclass
class Eintrag:
    """Ein Wert aus der abgeglichenen Datei."""

    name: str                                 # Farbrolle oder Schlüssel wie radius, schrift-sans
    thema: str                                # hell oder dunkel bei Farben, sonst leer
    ist: str                                  # so, wie er in der Datei steht
    zeile: int
    verweis: tuple[str, str] | None = None    # (Rolle, Thema), wenn der Wert auf eine Farbrolle zeigt


# Was ein Leser liefert: Einträge, unbekannte Namen (Name, Zeile) und Unlesbares (Name, Zeile, Grund).
Gelesen = tuple[list[Eintrag], list[tuple[str, int]], list[tuple[str, int, str]]]


@dataclass
class Befund:
    art: str                                  # abweichung, alte-glut, fehlt oder unbekannt
    name: str
    thema: str
    text: str

    @property
    def kennung(self) -> str:
        return " ".join(x for x in (self.art, self.name, self.thema) if x)


class Zeilen:
    """Zeilennummer zu einer Stelle im Text. Die Zeilenanfänge werden einmal gezählt."""

    def __init__(self, text: str) -> None:
        self.anfaenge = [0] + [m.end() for m in re.finditer("\n", text)]

    def __call__(self, stelle: int) -> int:
        return bisect.bisect_right(self.anfaenge, stelle)


def ohne_kommentare(text: str, zeilenkommentare: bool) -> str:
    """Ersetzt Kommentare durch Leerzeichen; Zeilenumbrüche und Zeichenketten bleiben stehen."""
    teile, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in "\"'":
            ende = i + 1
            while ende < n and text[ende] != c and text[ende] != "\n":
                ende += 2 if text[ende] == "\\" else 1
            teile.append(text[i:ende + 1])
            i = ende + 1
        elif text.startswith("/*", i):
            ende = text.find("*/", i + 2)
            ende = n if ende < 0 else ende + 2
            teile.append(re.sub(r"[^\n]", " ", text[i:ende]))
            i = ende
        elif zeilenkommentare and text.startswith("//", i):
            ende = text.find("\n", i)
            ende = n if ende < 0 else ende
            teile.append(" " * (ende - i))
            i = ende
        else:
            teile.append(c)
            i += 1
    return "".join(teile)


def namen(daten: dict) -> dict[str, tuple[str, str]]:
    """Namen ohne Präfix -> ("farbe", Rolle) oder ("wert", Schlüssel), wie CSS und Sass sie nutzen."""
    n = {f["rolle"]: ("farbe", f["rolle"]) for f in daten["farben"]}
    n.update({k: ("wert", k) for k in ("radius", "fokus-staerke", "fokus-abstand")})
    n.update({k: ("wert", f"schrift-{k}") for k in daten["schrift"]})
    n.update({f"groesse-{s['rolle']}": ("wert", f"groesse-{s['rolle']}") for s in daten["groessen"]["stufen"]})
    n.update({f"abstand-{a['stufe']}": ("wert", f"abstand-{a['stufe']}") for a in daten["abstaende"]})
    n.update({k: ("wert", k) for k in daten["satz"]})
    return n


def css_thema(stapel: list[str]) -> str:
    """Hell im Grundblock, dunkel unter prefers-color-scheme: dark und [data-theme="dark"]."""
    thema = "hell"
    for vorspann in stapel:
        v = re.sub(r"\s+", "", vorspann.lower())
        if v.startswith("@media"):
            # "not" vor dem Merkmal kehrt die Abfrage um: @media not all and (prefers-color-scheme: dark)
            nicht = "not" in v.split("prefers-color-scheme")[0]
            if "prefers-color-scheme:dark" in v:
                thema = "hell" if nicht else "dunkel"
            elif "prefers-color-scheme:light" in v:
                thema = "dunkel" if nicht else "hell"
        elif not v.startswith("@"):
            v = re.sub(r":not\([^)]*\)+", "", v)
            if re.search(r"\[data-theme=[\"']?dark[\"']?\]", v):
                thema = "dunkel"
            elif re.search(r"\[data-theme=[\"']?light[\"']?\]", v):
                thema = "hell"
    return thema


def css_name(name: str) -> str:
    """Löst CSS-Escapes im Namen auf, wie Browser es tun: --fs-gl\\75 t ist --fs-glut."""
    def zeichen(m: re.Match) -> str:
        if m.group(1) is None:
            return m.group(2)
        wert = int(m.group(1), 16)
        return chr(wert) if 0 < wert <= 0x10FFFF and not 0xD800 <= wert <= 0xDFFF else "\ufffd"

    return re.sub(r"\\([0-9a-fA-F]{1,6})[ \t\n]?|\\(.)", zeichen, name)


def css_deklarationen(text: str):
    """Liefert (Name, Wert, Zeile, Thema) für jede Custom Property in einem Block.

    Eine Zeichenkette endet spätestens am Zeilenende, wie im Browser (bad-string):
    Sonst verdeckte ein offenes Anführungszeichen alle folgenden Deklarationen."""
    rein = ohne_kommentare(text, zeilenkommentare=False)
    zeile_bei = Zeilen(rein)
    stapel: list[str] = []
    start, i, n, zeichen = 0, 0, len(rein), None
    while i < n:
        c = rein[i]
        if zeichen:
            if c == "\\":
                i += 1
            elif c == zeichen or c == "\n":
                zeichen = None
        elif c in "\"'":
            zeichen = c
        elif c in "{};":
            stueck = rein[start:i]
            if c == "{":
                stapel.append(stueck.strip())
            else:
                m = re.match(r"\s*(--(?:[A-Za-z0-9_-]|\\[0-9a-fA-F]{1,6}[ \t]?|\\[^\n])+)\s*:(.*)\Z", stueck, re.S)
                if m and stapel:
                    zeile = zeile_bei(start + m.start(1))
                    yield css_name(m.group(1)), " ".join(m.group(2).split()), zeile, css_thema(stapel)
                if c == "}" and stapel:
                    stapel.pop()
            start = i + 1
        i += 1


def verweis_auf(wert: str, muster: str, rollen: set[str], thema: str) -> tuple[str, str] | None:
    m = re.fullmatch(muster, wert)
    if not m or m.group(1) not in rollen:
        return None
    return m.group(1), thema


def css_lesen(daten: dict, text: str) -> Gelesen:
    alle = namen(daten)
    rollen = {f["rolle"] for f in daten["farben"]}
    eintraege, unbekannt = [], []
    for name, wert, zeile, thema in css_deklarationen(text):
        if name.startswith("--wp--preset--color--"):
            ziel = alle.get(name.removeprefix("--wp--preset--color--"))
            if ziel is None or ziel[0] != "farbe":
                continue
        elif name.startswith("--fs-"):
            ziel = alle.get(name.removeprefix("--fs-"))
            if ziel is None:
                unbekannt.append((name, zeile))
                continue
        else:
            continue
        art, schluessel = ziel
        if art == "farbe":
            verweis = verweis_auf(wert, r"var\(\s*--(?:fs-|wp--preset--color--)([a-z-]+)\s*(?:,[^)]*)?\)",
                                  rollen, thema)
            eintraege.append(Eintrag(schluessel, thema, wert, zeile, verweis))
        else:
            eintraege.append(Eintrag(schluessel, "", wert, zeile))
    return eintraege, unbekannt, []


def scss_wert(text: str, start: int) -> tuple[str, int]:
    """Wert einer Sass-Variable: bis zum Semikolon oder bis zum Zeilenende ohne Komma davor."""
    tiefe, i, zeichen = 0, start, None
    while i < len(text):
        c = text[i]
        if zeichen:
            if c == "\\":
                i += 1
            elif c == zeichen or c == "\n":
                zeichen = None
        elif c in "\"'":
            zeichen = c
        elif c == "(":
            tiefe += 1
        elif c == ")":
            tiefe -= 1
        elif tiefe <= 0 and (c in ";}" or (c == "\n" and not text[start:i].rstrip().endswith(","))):
            if text[start:i].strip():
                return text[start:i], i
        i += 1
    return text[start:], len(text)


def sass_map(wert: str) -> list[tuple[str, str, int]]:
    """Einträge einer Sass-Map als (Schlüssel, Wert, Abstand zum Anfang)."""
    m = re.fullmatch(r"\s*\((.*)\)\s*", wert, re.S)
    if not m:
        return []
    innen, versatz = m.group(1), m.start(1)
    teile, tiefe, anfang = [], 0, 0
    for i, c in enumerate(innen + ","):
        if c == "(":
            tiefe += 1
        elif c == ")":
            tiefe -= 1
        elif c == "," and tiefe == 0:
            teile.append((innen[anfang:i], versatz + anfang))
            anfang = i + 1
    eintraege = []
    for teil, stelle in teile:
        # Sass behandelt "glut" und glut als denselben Schlüssel.
        e = re.match(r"(\s*)([\"']?)([A-Za-z0-9_-]+)\2\s*:\s*(.*?)\s*\Z", teil, re.S)
        if e:
            eintraege.append((e.group(3), " ".join(e.group(4).split()), stelle + len(e.group(1))))
        elif teil.strip():
            return []
    return eintraege


def scss_verweis(wert: str, rollen: set[str]) -> tuple[str, str] | None:
    m = re.fullmatch(r"\$fs[-_]([a-z_-]+)", wert)
    if not m:
        return None
    ziel = m.group(1).replace("_", "-")
    if ziel.endswith("-dunkel") and ziel.removesuffix("-dunkel") in rollen:
        return ziel.removesuffix("-dunkel"), "dunkel"
    return (ziel, "hell") if ziel in rollen else None


def scss_lesen(daten: dict, text: str) -> Gelesen:
    alle = namen(daten)
    rollen = {f["rolle"] for f in daten["farben"]}
    rein = ohne_kommentare(text, zeilenkommentare=True)
    zeile_bei = Zeilen(rein)
    eintraege, unbekannt, unlesbar = [], [], []
    # Sass behandelt - und _ in Namen gleich: $fs_glut ist $fs-glut.
    for m in re.finditer(r"\$(fs[-_][A-Za-z0-9_-]+)\s*:", rein):
        roh, _ = scss_wert(rein, m.end())
        roh = re.sub(r"\s*!(?:default|global)\b", "", roh)
        wert = " ".join(roh.split())
        zeile = zeile_bei(m.start())
        name = m.group(1).replace("_", "-")
        kurz = name.removeprefix("fs-")
        if kurz in THEMEN:
            eintraege_map = sass_map(roh.strip())
            if not eintraege_map:
                # map.merge(), map.set() und Ähnliches lässt sich nicht auswerten.
                unlesbar.append((f"${name}", zeile, "keine Map-Schreibweise (key: wert, …)"))
                continue
            anfang = m.end() + (len(roh) - len(roh.lstrip()))
            for schluessel, w, stelle in eintraege_map:
                z = zeile_bei(anfang + stelle)
                schluessel = schluessel.replace("_", "-")
                if schluessel in rollen:
                    eintraege.append(Eintrag(schluessel, kurz, w, z, scss_verweis(w, rollen)))
                else:
                    unbekannt.append((f"${name}.{schluessel}", z))
            continue
        if kurz in ("groessen", "abstaende"):
            continue
        thema = "hell"
        if kurz.endswith("-dunkel") and kurz.removesuffix("-dunkel") in rollen:
            kurz, thema = kurz.removesuffix("-dunkel"), "dunkel"
        ziel = alle.get(kurz)
        if ziel is None:
            unbekannt.append((f"${name}", zeile))
        elif ziel[0] == "farbe":
            eintraege.append(Eintrag(kurz, thema, wert, zeile, scss_verweis(wert, rollen)))
        else:
            eintraege.append(Eintrag(ziel[1], "", wert, zeile))
    return eintraege, unbekannt, unlesbar


def xaml_elemente(text: str) -> list[dict]:
    """Liest XAML ohne DTD und Entitäten. Jedes Element mit Schlüssel, Thema, Zeile und Text."""
    parser = expat.ParserCreate(namespace_separator="|")

    def verbieten(*_args) -> None:
        raise Unbrauchbar("DOCTYPE und ENTITY sind in XAML nicht erlaubt")

    parser.StartDoctypeDeclHandler = verbieten
    parser.EntityDeclHandler = verbieten
    stapel: list[dict] = []
    elemente: list[dict] = []

    def anfang(name: str, attrs: dict) -> None:
        lokal = name.rsplit("|", 1)[-1]
        eltern = stapel[-1] if stapel else None
        schluessel = attrs.get(f"{XAML_NS}|Key")
        themen = (lokal == "ResourceDictionary" and eltern is not None
                  and eltern["lokal"] == "ResourceDictionary.ThemeDictionaries")
        thema = schluessel if themen else (eltern["thema"] if eltern else None)
        e = {"lokal": lokal, "schluessel": schluessel, "thema": thema, "zeile": parser.CurrentLineNumber,
             "attrs": {k.rsplit("|", 1)[-1]: v for k, v in attrs.items()}, "text": [], "themenwoerterbuch": themen}
        stapel.append(e)
        elemente.append(e)

    def ende(_name: str) -> None:
        stapel.pop()

    def zeichen(daten: str) -> None:
        if stapel:
            stapel[-1]["text"].append(daten)

    parser.StartElementHandler = anfang
    parser.EndElementHandler = ende
    parser.CharacterDataHandler = zeichen
    try:
        parser.Parse(text.encode("utf-8"), True)
    except expat.ExpatError as fehler:
        raise Unbrauchbar(f"kein gültiges XML: {fehler}") from None
    for e in elemente:
        e["text"] = " ".join("".join(e["text"]).split())
    return elemente


def avalonia_lesen(daten: dict, text: str) -> Gelesen:
    rolle_von = {pascal(f["rolle"]): f["rolle"] for f in daten["farben"]}
    rollen = set(rolle_von.values())
    werte = {"ControlCornerRadius": "radius", "OverlayCornerRadius": "radius",
             "Fs.FocusThickness": "fokus-staerke", "Fs.FocusOffset": "fokus-abstand"}
    werte.update({f"Fs.Font.{pascal(k)}": f"schrift-{k}" for k in daten["schrift"]})
    werte.update({f"Fs.Groesse.{pascal(s['rolle'])}": f"groesse-{s['rolle']}" for s in daten["groessen"]["stufen"]})
    werte.update({f"Fs.Abstand.{a['stufe']}": f"abstand-{a['stufe']}" for a in daten["abstaende"]})
    werte.update({xaml_satz(k): k for k in daten["satz"]})
    themen = {"Light": "hell", "Default": "hell", "Dark": "dunkel"}
    eintraege, unbekannt = [], []
    for e in xaml_elemente(text):
        k = e["schluessel"]
        if e["themenwoerterbuch"]:
            if k not in themen:
                unbekannt.append((f"Themenwörterbuch {k}", e["zeile"]))
            continue
        if not k:
            continue
        wert = e["attrs"].get("Color", "") if e["lokal"] == "SolidColorBrush" else e["text"]
        if k in werte:
            eintraege.append(Eintrag(werte[k], "", wert, e["zeile"]))
            continue
        m = re.fullmatch(r"Fs\.([A-Za-z]+)(\.Color)?", k)
        if not m or m.group(1) not in rolle_von:
            if k.startswith("Fs."):
                unbekannt.append((k, e["zeile"]))
            continue
        # Ein Eintrag außerhalb der Themenwörterbücher gilt in jedem Thema: Avalonia sucht im
        # Wörterbuch selbst, bevor es in ThemeDictionaries schaut (ResourceDictionary.TryGetResource).
        if e["thema"] is None:
            gilt_fuer = list(THEMEN)
        elif themen.get(e["thema"]) is not None:
            gilt_fuer = [themen[e["thema"]]]
        else:
            continue
        ref = re.fullmatch(r"\{(?:Static|Dynamic|Theme)Resource\s+Fs\.([A-Za-z]+)(?:\.Color)?\s*\}", wert)
        for thema in gilt_fuer:
            verweis = None
            if ref and rolle_von.get(ref.group(1)) in rollen:
                verweis = (rolle_von[ref.group(1)], thema)
            eintraege.append(Eintrag(rolle_von[m.group(1)], thema, wert, e["zeile"], verweis))
    return eintraege, unbekannt, []


def wp_slug(slug: str) -> str:
    """Slug so, wie WordPress ihn zur CSS-Variable macht (_wp_to_kebab_case): Glut wird glut,
    flaecheTief wird flaeche-tief."""
    gross, klein = "A-Z\u00c0-\u00d6\u00d8-\u00de", "a-z\u00df-\u00f6\u00f8-\u00ff"
    woerter = re.findall(f"[{gross}]?[{klein}]+|[{gross}]+(?![{klein}])|\\d+|[{gross}]", slug.replace("'", ""))
    return "-".join(woerter).lower()


def wordpress_lesen(daten: dict, text: str) -> Gelesen:
    try:
        theme = json.loads(text)
    except json.JSONDecodeError as fehler:
        raise Unbrauchbar(f"kein gültiges JSON: {fehler}") from None
    except (RecursionError, ValueError) as fehler:
        raise Unbrauchbar(f"JSON lässt sich nicht lesen: {type(fehler).__name__}") from None
    if not isinstance(theme, dict):
        raise Unbrauchbar("theme.json muss ein Objekt sein")
    zeile_bei = Zeilen(text)

    def zeile(slug: str) -> int:
        m = re.search(r'"slug"\s*:\s*"' + re.escape(slug) + '"', text)
        return zeile_bei(m.start()) if m else 0

    def holen(*pfad):
        wert = theme
        for schritt in pfad:
            wert = wert.get(schritt) if isinstance(wert, dict) else None
        return wert

    def liste(*pfad) -> list[dict]:
        """Einträge mit Slug, nach dem Slug, den WordPress daraus macht; der letzte gewinnt wie dort."""
        wert = holen(*pfad)
        if not isinstance(wert, list):
            return []
        nach_slug: dict[str, dict] = {}
        for x in wert:
            if isinstance(x, dict) and isinstance(x.get("slug"), str):
                nach_slug[wp_slug(x["slug"])] = dict(x, slug=wp_slug(x["slug"]), roh=x["slug"])
        return list(nach_slug.values())

    rollen = {f["rolle"] for f in daten["farben"]}
    groesse_von = {s["wordpress"]: s["rolle"] for s in daten["groessen"]["stufen"]}
    stufen = {a["stufe"] for a in daten["abstaende"]}
    eintraege, unbekannt = [], []
    for p in liste("settings", "color", "palette"):
        if p["slug"] in rollen:
            eintraege.append(Eintrag(p["slug"], "hell", str(p.get("color", "")), zeile(p["roh"])))
        else:
            unbekannt.append((f"Palette {p['roh']}", zeile(p["roh"])))
    for s in liste("settings", "typography", "fontFamilies"):
        if s["slug"] in daten["schrift"]:
            eintraege.append(Eintrag(f"schrift-{s['slug']}", "", str(s.get("fontFamily", "")), zeile(s["roh"])))
    for s in liste("settings", "typography", "fontSizes"):
        if s["slug"] in groesse_von:
            fluid = s.get("fluid") if isinstance(s.get("fluid"), dict) else {}
            ist = wp_groesse(str(s.get("size", "")), fluid.get("min"), fluid.get("max"))
            eintraege.append(Eintrag(f"groesse-{groesse_von[s['slug']]}", "", ist, zeile(s["roh"])))
    for s in liste("settings", "spacing", "spacingSizes"):
        if s["slug"] in stufen:
            eintraege.append(Eintrag(f"abstand-{s['slug']}", "", str(s.get("size", "")), zeile(s["roh"])))
    # Die Fensterbreiten der fließenden Größen. Ohne fluid oder mit false rechnet WordPress nicht
    # fließend; ohne eigene Breiten gelten 320px und layout.wideSize, sonst 1600px.
    fluid, breit = holen("settings", "typography", "fluid"), holen("settings", "layout", "wideSize")
    if fluid in (None, False):
        ist = "aus"
    else:
        f = fluid if isinstance(fluid, dict) else {}
        ist = f"{f.get('minViewportWidth') or '320px'} bis " \
              f"{f.get('maxViewportWidth') or (breit if isinstance(breit, str) and breit else '1600px')}"
        if f.get("minFontSize"):
            ist += f", minFontSize {f['minFontSize']}"
    eintraege.append(Eintrag("fluessig", "", ist, 0))
    for schluessel, pfad in (("zeilenhoehe-text", ("styles", "typography", "lineHeight")),
                             ("zeilenhoehe-ueberschrift", ("styles", "elements", "heading", "typography", "lineHeight")),
                             ("staerke-ueberschrift", ("styles", "elements", "heading", "typography", "fontWeight"))):
        wert = holen(*pfad)
        if wert is not None:
            eintraege.append(Eintrag(schluessel, "", str(wert), 0))
    return eintraege, unbekannt, []


LESER = {"css": css_lesen, "scss": scss_lesen, "avalonia": avalonia_lesen, "wordpress": wordpress_lesen}


def soll_werte(daten: dict, fmt: str) -> dict[str, tuple[str, str]]:
    """Werte ohne Thema, die das Format trägt: Schlüssel -> (Soll, Vergleichsart)."""
    xaml = fmt == "avalonia"
    form, satz = daten["form"], daten["satz"]
    w: dict[str, tuple[str, str]] = {}
    if fmt != "wordpress":
        w.update({k: (form[k], "laenge") for k in ("radius", "fokus-staerke", "fokus-abstand")})
    w.update({f"schrift-{k}": (v["xaml" if xaml else "css"], "schrift") for k, v in daten["schrift"].items()})
    for s in daten["groessen"]["stufen"]:
        if xaml:
            soll = (px(s["wert"]), "laenge")
        elif fmt == "wordpress":
            soll = (wp_groesse(s["wert"], s.get("min"), s.get("max")), "text")
        else:
            soll = (css_groesse(daten, s), "text")
        w[f"groesse-{s['rolle']}"] = soll
    w.update({f"abstand-{a['stufe']}": (px(a["wert"]) if xaml else a["wert"], "laenge") for a in daten["abstaende"]})
    w["zeilenhoehe-text"] = (satz["zeilenhoehe-text"], "zahl")
    w["zeilenhoehe-ueberschrift"] = (satz["zeilenhoehe-ueberschrift"], "zahl")
    w["staerke-ueberschrift"] = (satz["staerke-ueberschrift"], "staerke")
    if fmt == "wordpress":
        fluessig = daten["groessen"]["fluessig"]
        w["fluessig"] = (f"{fluessig['von']} bis {fluessig['bis']}", "fluessig")
    return w


def soll_farben(daten: dict, fmt: str) -> list[tuple[str, str]]:
    """(Rolle, Thema), die das Format trägt. theme.json kennt nur die hellen Farben mit eigenem Wert."""
    if fmt == "wordpress":
        return [(f["rolle"], "hell") for f in daten["farben"] if not f["hell"].startswith("=")]
    return [(f["rolle"], t) for t in THEMEN for f in daten["farben"]]


def farbe_normal(wert: str, xaml: bool) -> str | None:
    w = wert.strip()
    if w.lower() in ("white", "black"):
        return "#FFFFFF" if w.lower() == "white" else "#000000"
    m = re.fullmatch(r"#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})", w)
    if not m:
        return None
    h = m.group(1).upper()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 8:
        deckkraft, h = (h[:2], h[2:]) if xaml else (h[6:], h[:6])
        if deckkraft != "FF":
            return None
    return "#" + h


def gleich(soll: str, ist: str, art: str, xaml: bool) -> bool:
    def einfach(x: str) -> str:
        return "".join(x.split()).lower()

    if art == "schrift":
        def liste(x: str) -> list[str]:
            return [" ".join(t.strip().strip("\"'").split()).lower() for t in x.split(",")]
        return liste(soll) == liste(ist)
    if art == "fluessig":
        # "320px bis 64rem", dazu höchstens minFontSize 14px, die Vorgabe von WordPress.
        def teile(x: str) -> tuple[Decimal, Decimal, Decimal] | None:
            m = re.fullmatch(r"(\S+) bis (\S+?)(?:, minFontSize (\S+))?", x.strip())
            if not m or not all(LAENGE.fullmatch(g) for g in m.groups() if g):
                return None
            return rem(m.group(1)), rem(m.group(2)), rem(m.group(3) or "14px")
        a, b = teile(soll), teile(ist)
        return a is not None and a == b
    if art == "staerke":
        def stufe(x: str) -> int | None:
            x = einfach(x)
            return int(x) if x.isdigit() else STAERKEN.get(x)
        return stufe(soll) is not None and stufe(soll) == stufe(ist)
    if art in ("laenge", "zahl"):
        def teile(x: str) -> tuple[Decimal, str] | None:
            m = re.fullmatch(r"(-?\d+(?:\.\d+)?|-?\.\d+)([a-z%]*)", einfach(x))
            if not m:
                return None
            einheit = m.group(2) or ("px" if xaml and art == "laenge" else "")
            return Decimal(m.group(1)), einheit
        a, b = teile(soll), teile(ist)
        if a is None or b is None:
            return False
        return a[0] == b[0] and (a[0] == 0 or a[1] == b[1])
    return einfach(soll) == einfach(ist)


def abgleich(daten: dict, pfad: Path, fmt: str | None) -> tuple[str, list[Befund], int]:
    """Gleicht eine Datei ab. Liefert Format, Befunde und die Zahl geprüfter Werte."""
    fmt = fmt or ENDUNGEN.get(pfad.suffix.lower())
    if fmt not in FORMATE:
        raise Unbrauchbar(f"Format unbekannt; bitte --format {' | '.join(FORMATE)} angeben")
    try:
        if not pfad.is_file():
            raise Unbrauchbar("keine Datei")
        if pfad.stat().st_size > GROESSTE_DATEI:
            raise Unbrauchbar("größer als 2 MB, das ist keine Kopie der Marke")
        text = pfad.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as fehler:
        raise Unbrauchbar(f"nicht lesbar: {fehler}") from None
    xaml = fmt == "avalonia"
    eintraege, unbekannt, unlesbar = LESER[fmt](daten, text)
    if not [e for e in eintraege if e.name != "fluessig"]:   # fluessig liest theme.json immer mit
        raise Unbrauchbar(f"keine Werte der Marke gefunden; ist das die Kopie, und stimmt das Format {fmt}?")
    befunde: list[Befund] = []
    wert = daten["wert"]
    # Ein Verweis zeigt zuerst auf den Wert, den die Datei der Rolle gibt, dann
    # auf einen weiteren Verweis. Nennt die Datei die Rolle gar nicht, gilt das Token.
    werte_der_datei: dict[tuple[str, str], Eintrag] = {}
    verweise_der_datei: dict[tuple[str, str], Eintrag] = {}
    for e in eintraege:
        if e.thema:
            ziel = werte_der_datei if e.verweis is None else verweise_der_datei
            ziel.setdefault((e.name, e.thema), e)

    def aufloesen(e: Eintrag, tiefe: int = 0) -> str:
        if e.verweis is None or tiefe > 10:
            return e.ist
        if e.verweis in werte_der_datei:
            return werte_der_datei[e.verweis].ist
        ziel = verweise_der_datei.get(e.verweis)
        if ziel is None:
            return wert[e.verweis[1]][e.verweis[0]]
        return e.ist if ziel is e else aufloesen(ziel, tiefe + 1)

    soll_w = soll_werte(daten, fmt)
    for e in eintraege:
        wo = f" (Zeile {e.zeile})" if e.zeile else ""
        if e.thema:
            soll, ist = wert[e.thema][e.name], aufloesen(e)
            if farbe_normal(ist, xaml) != soll:
                zusatz = f" = {ist}" if e.verweis else ""
                befunde.append(Befund("abweichung", e.name, e.thema,
                                      f"Abweichung: {e.name}, {e.thema}: Soll {soll}, Ist {e.ist}{zusatz}{wo}"))
        elif e.name in soll_w:
            soll, art = soll_w[e.name]
            if not gleich(soll, e.ist, art, xaml):
                befunde.append(Befund("abweichung", e.name, "",
                                      f"Abweichung: {e.name}: Soll {soll}, Ist {e.ist}{wo}"))
    da = {(e.name, e.thema) for e in eintraege}
    for rolle, thema in soll_farben(daten, fmt):
        if (rolle, thema) not in da:
            befunde.append(Befund("fehlt", rolle, thema, f"fehlt: {rolle}, {thema}"))
    for schluessel in soll_w:
        if (schluessel, "") not in da:
            befunde.append(Befund("fehlt", schluessel, "", f"fehlt: {schluessel}"))
    zeile_bei = Zeilen(text)
    for name, zeile, grund in unlesbar:
        befunde.append(Befund("unlesbar", name, "", f"nicht auswertbar: {name} (Zeile {zeile}): {grund}"))
    for m in ALTE_GLUT.finditer(text):
        befunde.append(Befund("alte-glut", m.group(0).upper(), "",
                              f"Alter Glutwert {m.group(0)} in Zeile {zeile_bei(m.start())}, "
                              f"heute hell {wert['hell']['glut']} und dunkel {wert['dunkel']['glut']}"))
    for name, zeile in unbekannt:
        befunde.append(Befund("unbekannt", name, "", f"unbekannt: {name}" + (f" (Zeile {zeile})" if zeile else "")))
    return fmt, befunde, len(eintraege)


def ist_fehler(b: Befund, streng: bool) -> bool:
    return b.art in ("abweichung", "alte-glut", "unlesbar") or (streng and b.art == "fehlt")


def abgleichen(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="marke.py abgleichen",
        description="Vergleicht die Kopie eines Projekts mit den Tokens. Liest die Datei nur.")
    parser.add_argument("datei", type=Path)
    parser.add_argument("--format", choices=FORMATE, help="sonst gilt die Endung (.css, .scss, .axaml, .json)")
    parser.add_argument("--streng", action="store_true", help="fehlende Rollen und Werte sind Fehler")
    args = parser.parse_args(argv)
    daten = laden()
    try:
        fmt, befunde, anzahl = abgleich(daten, args.datei, args.format)
    except Unbrauchbar as fehler:
        print(f"{args.datei}: {fehler}", file=sys.stderr)
        return 2
    fehler = [b for b in befunde if ist_fehler(b, args.streng)]
    hinweise = [b for b in befunde if not ist_fehler(b, args.streng)]
    print(f"Abgleich {args.datei} ({fmt}) mit {TOKENS} Version {daten['version']}:")
    for b in fehler:
        print(f"  FEHLER {b.text}")
    for b in hinweise:
        print(f"  Hinweis {b.text}")
    if fehler:
        print(f"Abweichung: {len(fehler)} Fehler, {len(hinweise)} Hinweise.")
        return 1
    print(f"Passt: {anzahl} Werte geprüft, {len(hinweise)} Hinweise.")
    return 0


# --- Rasterbilder ----------------------------------------------------------------

RASTER = "exporte/raster"
RASTER_LISTE = "exporte/raster/quellen.json"
SYMBOL = "logos/firestrike-symbol.svg"
# Wie groß das Symbol auf breiten Flächen (MSIX Wide und SplashScreen) ist, als Anteil der Höhe.
SYMBOL_ANTEIL = 0.5

# Datei unter exporte/raster -> (Quell-SVG, Größen als (Breite, Höhe)). ICO-Dateien tragen mehrere Größen.
RASTERBILDER: dict[str, tuple[str, tuple[tuple[int, int], ...]]] = {
    "favicon.ico": (SYMBOL, ((16, 16), (32, 32), (48, 48))),
    "favicon-32.png": (SYMBOL, ((32, 32),)),
    "site-icon-512.png": (SYMBOL, ((512, 512),)),
    "apple-touch-icon-180.png": (SYMBOL, ((180, 180),)),
    "profilbild-400.png": (SYMBOL, ((400, 400),)),
    "app.ico": (SYMBOL, tuple((g, g) for g in (16, 20, 24, 32, 40, 48, 64, 256))),
    **{f"msix/Square44x44Logo.scale-{s}.png": (SYMBOL, ((44 * s // 100, 44 * s // 100),)) for s in (100, 200)},
    **{f"msix/Square44x44Logo.targetsize-{g}.png": (SYMBOL, ((g, g),)) for g in (16, 24, 32, 48, 256)},
    **{f"msix/Square150x150Logo.scale-{s}.png": (SYMBOL, ((150 * s // 100, 150 * s // 100),)) for s in (100, 200)},
    **{f"msix/StoreLogo.scale-{s}.png": (SYMBOL, ((50 * s // 100, 50 * s // 100),)) for s in (100, 200)},
    **{f"msix/Wide310x150Logo.scale-{s}.png": (SYMBOL, ((310 * s // 100, 150 * s // 100),)) for s in (100, 200)},
    **{f"msix/SplashScreen.scale-{s}.png": (SYMBOL, ((620 * s // 100, 300 * s // 100),)) for s in (100, 200)},
}


def sha256(pfad: Path) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()


def png_masse(daten: bytes) -> tuple[int, int] | None:
    """Breite und Höhe aus dem IHDR-Block, ohne die Bilddaten zu lesen."""
    if len(daten) < 24 or daten[:8] != b"\x89PNG\r\n\x1a\n" or daten[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", daten[16:24])


def ico_bauen(bilder: list[bytes]) -> bytes:
    """ICO mit PNG-Einträgen (Windows ab Vista, alle Browser)."""
    kopf = struct.pack("<HHH", 0, 1, len(bilder))
    eintraege, rumpf = b"", b""
    versatz = 6 + 16 * len(bilder)
    for png in bilder:
        breite, hoehe = png_masse(png)
        eintraege += struct.pack("<BBBBHHII", breite % 256, hoehe % 256, 0, 0, 1, 32, len(png), versatz + len(rumpf))
        rumpf += png
    return kopf + eintraege + rumpf


def ico_masse(daten: bytes) -> list[tuple[int, int]] | None:
    """Größen der Einträge einer ICO-Datei; jeder Eintrag muss ein PNG passender Größe sein."""
    if len(daten) < 6:
        return None
    reserviert, art, anzahl = struct.unpack("<HHH", daten[:6])
    if reserviert != 0 or art != 1 or len(daten) < 6 + 16 * anzahl:
        return None
    masse = []
    for i in range(anzahl):
        b, h, _, _, _, _, laenge, versatz = struct.unpack("<BBBBHHII", daten[6 + 16 * i:22 + 16 * i])
        png = png_masse(daten[versatz:versatz + laenge])
        if png is None or png != (b or 256, h or 256):
            return None
        masse.append(png)
    return masse


def svg_innen(text: str) -> tuple[str, str]:
    """viewBox und Inhalt des Wurzelelements."""
    wurzel = re.search(r"<svg\b[^>]*>", text)
    box = re.search(r'viewBox="([^"]+)"', wurzel.group(0))
    return box.group(1), text[wurzel.end():text.rindex("</svg>")]


def rendern(werkzeug: str, quelle: Path, breite: int, hoehe: int, arbeit: Path) -> bytes:
    """Rendert das SVG mit rsvg-convert; auf breiten Flächen mittig mit Rand, ohne Verzerrung."""
    if breite == hoehe:
        datei = quelle
    else:
        box, innen = svg_innen(quelle.read_text(encoding="utf-8"))
        seite = round(hoehe * SYMBOL_ANTEIL)
        datei = arbeit / f"breit-{breite}x{hoehe}.svg"
        datei.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{breite}" height="{hoehe}" '
            f'viewBox="0 0 {breite} {hoehe}"><svg x="{(breite - seite) // 2}" y="{(hoehe - seite) // 2}" '
            f'width="{seite}" height="{seite}" viewBox="{box}">{innen}</svg></svg>', encoding="utf-8")
    ergebnis = subprocess.run([werkzeug, "--format", "png", "--width", str(breite), "--height", str(hoehe), str(datei)],
                              check=True, capture_output=True, timeout=60)
    if png_masse(ergebnis.stdout) != (breite, hoehe):
        raise SystemExit(f"{quelle}: rsvg-convert lieferte kein PNG mit {breite} x {hoehe}")
    return ergebnis.stdout


def raster() -> int:
    werkzeug = os.environ.get("RSVG_CONVERT") or shutil.which("rsvg-convert")
    if not werkzeug:
        print("rsvg-convert fehlt: Paket librsvg2-bin installieren oder RSVG_CONVERT setzen.", file=sys.stderr)
        return 2
    version = subprocess.run([werkzeug, "--version"], check=True, capture_output=True, text=True,
                             timeout=30).stdout.splitlines()[0].strip()
    ziel = WURZEL / RASTER
    liste = {"werkzeug": version, "bilder": {}}
    with tempfile.TemporaryDirectory() as tmp:
        for name, (quelle, groessen) in RASTERBILDER.items():
            bilder = [rendern(werkzeug, WURZEL / quelle, b, h, Path(tmp)) for b, h in groessen]
            inhalt = ico_bauen(bilder) if name.endswith(".ico") else bilder[0]
            datei = ziel / name
            datei.parent.mkdir(parents=True, exist_ok=True)
            if not datei.is_file() or datei.read_bytes() != inhalt:
                datei.write_bytes(inhalt)
                print(f"geschrieben: {RASTER}/{name}")
            liste["bilder"][name] = {"quelle": quelle, "quelle_sha256": sha256(WURZEL / quelle),
                                     "groessen": [f"{b}x{h}" for b, h in groessen]}
    text = json.dumps(liste, ensure_ascii=False, indent=2) + "\n"
    if not (WURZEL / RASTER_LISTE).is_file() or (WURZEL / RASTER_LISTE).read_text(encoding="utf-8") != text:
        (WURZEL / RASTER_LISTE).write_text(text, encoding="utf-8", newline="\n")
        print(f"geschrieben: {RASTER_LISTE}")
    return 0


def raster_pruefen() -> tuple[list[str], int]:
    """Jedes Rasterbild passt zum Stand seiner Quelle (Prüfsumme in der Liste) und hat die richtigen Maße."""
    hinweis = "bitte python3 werkzeuge/marke.py raster"
    pfad = WURZEL / RASTER_LISTE
    if not pfad.is_file():
        return [f"fehlt: {RASTER_LISTE}, {hinweis}"], 0
    liste = json.loads(pfad.read_text(encoding="utf-8"))["bilder"]
    fehler = []
    vorhanden = {p.relative_to(WURZEL / RASTER).as_posix() for p in (WURZEL / RASTER).rglob("*") if p.is_file()}
    for name in sorted(vorhanden - set(RASTERBILDER) - {"quellen.json"}):
        fehler.append(f"{RASTER}/{name}: steht nicht in RASTERBILDER, also nicht erzeugt")
    for name, (quelle, groessen) in RASTERBILDER.items():
        eintrag, datei = liste.get(name), WURZEL / RASTER / name
        if eintrag is None or not datei.is_file():
            fehler.append(f"fehlt: {RASTER}/{name}, {hinweis}")
            continue
        if eintrag["quelle"] != quelle or eintrag["quelle_sha256"] != sha256(WURZEL / quelle):
            fehler.append(f"veraltet: {RASTER}/{name}, {quelle} hat sich geändert, {hinweis}")
        soll = [(b, h) for b, h in groessen]
        if eintrag["groessen"] != [f"{b}x{h}" for b, h in soll]:
            fehler.append(f"veraltet: {RASTER}/{name}, Größen in der Liste stimmen nicht, {hinweis}")
        inhalt = datei.read_bytes()
        ist = ico_masse(inhalt) if name.endswith(".ico") else ([m] if (m := png_masse(inhalt)) else None)
        if ist != soll:
            fehler.append(f"{RASTER}/{name}: Maße {ist}, erwartet {soll}")
    for name in sorted(set(liste) - set(RASTERBILDER)):
        fehler.append(f"{RASTER_LISTE}: {name} gibt es nicht mehr, {hinweis}")
    return fehler, len(RASTERBILDER)


# --- Wortmarke als Pfade ---------------------------------------------------------

WORTMARKE_SCHRIFT = ("Liberation Sans", "Bold")
PFADE_QUELLE = "logos/quellen/quelle.json"
# Logo mit Pfaden -> Logo mit Text, aus dem es entsteht. Die Text-Fassungen sind die
# Quelle zum Bearbeiten (Laufweite, Lage); die Logos selbst tragen nur noch Pfade.
PFAD_LOGOS = {
    "logos/firestrike-logo-light.svg": "logos/quellen/firestrike-logo-light-text.svg",
    "logos/firestrike-logo-dark.svg": "logos/quellen/firestrike-logo-dark-text.svg",
}


class Schrift:
    """Liest aus einer TrueType-Datei nur, was die Wortmarke braucht: Namen, Maße, Zeichen und Umrisse."""

    def __init__(self, pfad: Path) -> None:
        self.d = pfad.read_bytes()
        if self.d[:4] not in (b"\x00\x01\x00\x00", b"true"):
            raise SystemExit(f"{pfad}: keine TrueType-Schrift")
        self.tabellen = {}
        for i in range(self.u16(4)):
            tag, _, versatz, laenge = struct.unpack(">4sIII", self.d[12 + 16 * i:28 + 16 * i])
            self.tabellen[tag.decode("latin-1")] = versatz
        fehlen = {"head", "hhea", "hmtx", "cmap", "loca", "glyf", "name", "maxp"} - set(self.tabellen)
        if fehlen:
            raise SystemExit(f"{pfad}: Tabellen {sorted(fehlen)} fehlen, die Umrisse müssen in glyf stehen")
        kopf = self.tabellen["head"]
        self.einheiten = self.u16(kopf + 18)
        self.loca_lang = self.s16(kopf + 50) == 1
        hhea = self.tabellen["hhea"]
        self.oben, self.unten, self.metriken = self.s16(hhea + 4), self.s16(hhea + 6), self.u16(hhea + 34)

    def u16(self, o: int) -> int:
        return struct.unpack(">H", self.d[o:o + 2])[0]

    def s16(self, o: int) -> int:
        return struct.unpack(">h", self.d[o:o + 2])[0]

    def name(self, nummer: int) -> str:
        o = self.tabellen["name"]
        anzahl, ablage = self.u16(o + 2), o + self.u16(o + 4)
        for i in range(anzahl):
            plattform, kodierung, sprache, nr, laenge, versatz = struct.unpack(">6H", self.d[o + 6 + 12 * i:o + 18 + 12 * i])
            if (plattform, kodierung, sprache, nr) == (3, 1, 0x409, nummer):
                return self.d[ablage + versatz:ablage + versatz + laenge].decode("utf-16-be")
        return ""

    def glyphe(self, zeichen: str) -> int:
        """Glyphennummer über cmap Format 4 (Unicode, BMP)."""
        o = self.tabellen["cmap"]
        for i in range(self.u16(o + 2)):
            plattform, kodierung, versatz = struct.unpack(">HHI", self.d[o + 4 + 8 * i:o + 12 + 8 * i])
            t = o + versatz
            if (plattform, kodierung) != (3, 1) or self.u16(t) != 4:
                continue
            segmente = self.u16(t + 6) // 2
            enden, anfaenge = t + 14, t + 16 + 2 * segmente
            deltas, verschiebungen = anfaenge + 2 * segmente, anfaenge + 4 * segmente
            c = ord(zeichen)
            for s in range(segmente):
                if self.u16(anfaenge + 2 * s) <= c <= self.u16(enden + 2 * s):
                    verschiebung = self.u16(verschiebungen + 2 * s)
                    if verschiebung == 0:
                        return (c + self.s16(deltas + 2 * s)) & 0xFFFF
                    g = self.u16(verschiebungen + 2 * s + verschiebung + 2 * (c - self.u16(anfaenge + 2 * s)))
                    return (g + self.s16(deltas + 2 * s)) & 0xFFFF if g else 0
        raise SystemExit(f"Zeichen {zeichen!r} fehlt in der Schrift")

    def vorschub(self, g: int) -> int:
        return self.u16(self.tabellen["hmtx"] + 4 * min(g, self.metriken - 1))

    def konturen(self, g: int) -> list[list[tuple[int, int, bool]]]:
        """Umrisse einer einfachen Glyphe als Konturen aus (x, y, auf der Kurve)."""
        loca = self.tabellen["loca"]
        if self.loca_lang:
            anfang, ende = struct.unpack(">II", self.d[loca + 4 * g:loca + 4 * g + 8])
        else:
            anfang, ende = (2 * x for x in struct.unpack(">HH", self.d[loca + 2 * g:loca + 2 * g + 4]))
        if anfang == ende:
            return []
        o = self.tabellen["glyf"] + anfang
        anzahl = self.s16(o)
        if anzahl < 0:
            raise SystemExit(f"Glyphe {g} ist zusammengesetzt; das braucht die Wortmarke nicht")
        enden = [self.u16(o + 10 + 2 * i) for i in range(anzahl)]
        p = o + 10 + 2 * anzahl
        p += 2 + self.u16(p)
        punkte = enden[-1] + 1
        flags: list[int] = []
        while len(flags) < punkte:
            f = self.d[p]
            p += 1
            flags.append(f)
            if f & 8:
                flags += [f] * self.d[p]
                p += 1

        def achse(kurz: int, gleich: int) -> list[int]:
            nonlocal p
            werte, wert = [], 0
            for f in flags:
                if f & kurz:
                    wert += self.d[p] if f & gleich else -self.d[p]
                    p += 1
                elif not f & gleich:
                    wert += self.s16(p)
                    p += 2
                werte.append(wert)
            return werte

        xs, ys = achse(2, 16), achse(4, 32)
        konturen, anfang = [], 0
        for ende in enden:
            konturen.append([(xs[i], ys[i], bool(flags[i] & 1)) for i in range(anfang, ende + 1)])
            anfang = ende + 1
        return konturen


def pfad_text(konturen, x0: float, y0: float, s: float) -> str:
    """TrueType-Konturen (quadratisch) als SVG-Pfad; y zeigt in SVG nach unten."""
    def z(v: float) -> str:
        return f"{round(v, 2):g}"

    def pkt(x: float, y: float) -> str:
        return f"{z(x0 + x * s)} {z(y0 - y * s)}"

    teile = []
    for kontur in konturen:
        if not kontur:
            continue
        start = next((i for i, (_, _, auf) in enumerate(kontur) if auf), None)
        if start is None:
            (ax, ay, _), (bx, by, _) = kontur[0], kontur[1]
            kontur = [((ax + bx) / 2, (ay + by) / 2, True)] + kontur
            start = 0
        kontur = kontur[start:] + kontur[:start]
        teile.append("M" + pkt(*kontur[0][:2]))
        offen = None
        for x, y, auf in kontur[1:] + [kontur[0]]:
            if auf:
                teile.append(("Q" + pkt(*offen) + " " if offen else "L") + pkt(x, y))
                offen = None
            elif offen:
                mx, my = (offen[0] + x) / 2, (offen[1] + y) / 2
                teile.append("Q" + pkt(*offen) + " " + pkt(mx, my))
                offen = (x, y)
            else:
                offen = (x, y)
        teile.append("Z")
    return "".join(teile)


def wortmarke(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Aufruf: python3 werkzeuge/marke.py wortmarke SCHRIFT.ttf (Liberation Sans Bold)", file=sys.stderr)
        return 2
    pfad = Path(argv[0])
    schrift = Schrift(pfad)
    familie, schnitt, version, lizenz = schrift.name(1), schrift.name(2), schrift.name(5), schrift.name(13)
    if (familie, schnitt) != WORTMARKE_SCHRIFT or "Open Font License" not in lizenz:
        kurz = (lizenz.splitlines() or ["ohne Lizenzangabe"])[0][:80]
        print(f"{pfad}: {familie} {schnitt} ({kurz}); "
              f"erwartet {' '.join(WORTMARKE_SCHRIFT)} unter der SIL Open Font License", file=sys.stderr)
        return 2
    quellen = {}
    for ziel, quelle in PFAD_LOGOS.items():
        text = (WURZEL / quelle).read_text(encoding="utf-8")
        treffer = list(re.finditer(r"<text\b([^>]*)>([^<]*)</text>", text))
        if len(treffer) != 1:
            raise SystemExit(f"{quelle}: erwartet genau ein <text>")
        attrs = dict(re.findall(r'([a-z-]+)="([^"]*)"', treffer[0].group(1)))
        if attrs.get("font-weight") != "700" or attrs.get("dominant-baseline") != "central":
            raise SystemExit(f"{quelle}: erwartet font-weight 700 und dominant-baseline central")
        groesse = float(attrs["font-size"])
        s = groesse / schrift.einheiten
        # dominant-baseline central: Mitte zwischen Ober- und Unterlänge aus hhea, wie Browser es rechnen
        grundlinie = float(attrs["y"]) + (schrift.oben + schrift.unten) / 2 * s
        x, teile = float(attrs["x"]), []
        for zeichen in treffer[0].group(2):
            g = schrift.glyphe(zeichen)
            teile.append(pfad_text(schrift.konturen(g), x, grundlinie, s))
            x += schrift.vorschub(g) * s + float(attrs.get("letter-spacing", "0"))
        element = f'<path d="{"".join(teile)}" fill="{attrs["fill"]}"/>'
        neu = text[:treffer[0].start()] + element + text[treffer[0].end():]
        (WURZEL / ziel).parent.mkdir(parents=True, exist_ok=True)
        (WURZEL / ziel).write_text(neu, encoding="utf-8", newline="\n")
        print(f"geschrieben: {ziel}")
        quellen[quelle] = sha256(WURZEL / quelle)
    liste = {"schrift": f"{familie} {schnitt}, {version}", "lizenz": lizenz,
             "schrift_sha256": sha256(pfad), "quellen": quellen}
    (WURZEL / PFADE_QUELLE).write_text(json.dumps(liste, ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8", newline="\n")
    print(f"geschrieben: {PFADE_QUELLE}; jetzt python3 werkzeuge/marke.py erzeugen für die einfarbigen")
    return 0


def pfade_pruefen() -> list[str]:
    """Die Logos mit Pfaden passen zum Stand der Logos mit Text und enthalten keinen Text mehr."""
    hinweis = "bitte python3 werkzeuge/marke.py wortmarke mit Liberation Sans Bold"
    if not (WURZEL / PFADE_QUELLE).is_file():
        return [f"fehlt: {PFADE_QUELLE}, {hinweis}"]
    quellen = json.loads((WURZEL / PFADE_QUELLE).read_text(encoding="utf-8"))["quellen"]
    fehler = []
    for ziel, quelle in PFAD_LOGOS.items():
        if not (WURZEL / ziel).is_file():
            fehler.append(f"fehlt: {ziel}, {hinweis}")
        elif "<text" in (WURZEL / ziel).read_text(encoding="utf-8"):
            fehler.append(f"{ziel}: enthält noch <text>")
        if quellen.get(quelle) != sha256(WURZEL / quelle):
            fehler.append(f"veraltet: {ziel}, {quelle} hat sich geändert, {hinweis}")
    return fehler


# --- Befehle --------------------------------------------------------------------

# Die eigenen Exporte, die pruefen mit abgleichen gegen die Tokens hält: Pfad -> streng
EIGENE_EXPORTE = {
    "exporte/firestrike.css": True,
    "exporte/_firestrike.scss": True,
    "exporte/avalonia/Firestrike.axaml": True,
    "exporte/wordpress/firestrike.json": True,
    "exporte/anmeldeseite.css": True,
    "exporte/wordpress/farben.css": False,
}
ABGLEICH_TESTS = "tests/abgleich/erwartet.json"


def cli(pfad: Path, *optionen: str) -> int:
    """Exit-Code von `marke.py abgleichen` als eigener Prozess, so wie ein Projekt es aufruft."""
    lauf = subprocess.run([sys.executable, str(WURZEL / "werkzeuge" / "marke.py"), "abgleichen", str(pfad), *optionen],
                          capture_output=True, text=True, timeout=120)
    return lauf.returncode


def abgleich_pruefen(daten: dict) -> tuple[list[str], int]:
    """Eigene Exporte und die Testdateien unter tests/abgleich, im Prozess und über den Befehl."""
    fehler, anzahl = [], 0
    for pfad, streng in EIGENE_EXPORTE.items():
        try:
            _, befunde, _ = abgleich(daten, WURZEL / pfad, None)
        except Unbrauchbar as f:
            fehler.append(f"abgleichen {pfad}: {f}")
            continue
        anzahl += 1
        fehler += [f"abgleichen {pfad}: {b.text}" for b in befunde if ist_fehler(b, streng)]
    tests = json.loads((WURZEL / ABGLEICH_TESTS).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        # Unbrauchbares, das nicht als Datei ins Repo gehört: zu groß und zu tief verschachtelt.
        erzeugt = {"erzeugt/zu-gross.css": ":root {\n" + "  --fs-glut: #A24C18;\n" * 130000 + "}\n",
                   "erzeugt/zu-tief.json": "[" * 100000 + "]" * 100000}
        for name, inhalt in erzeugt.items():
            (Path(tmp) / name).parent.mkdir(exist_ok=True)
            (Path(tmp) / name).write_text(inhalt, encoding="utf-8")
            tests[name] = {"exit": 2, "exit_streng": 2, "befunde": None}
        for name, erwartet in tests.items():
            pfad = (Path(tmp) if name in erzeugt else WURZEL / "tests" / "abgleich") / name
            anzahl += 1
            try:
                _, befunde, _ = abgleich(daten, pfad, None)
            except Unbrauchbar as f:
                if erwartet["befunde"] is not None:
                    fehler.append(f"Abgleichtest {name}: {f}")
                befunde = None
            if erwartet["befunde"] is None and befunde is not None:
                fehler.append(f"Abgleichtest {name}: hätte als unbrauchbar abgelehnt werden müssen")
            elif befunde is not None:
                ist, soll = Counter(b.kennung for b in befunde), Counter(erwartet["befunde"])
                if ist != soll:
                    zu_viel = sorted((ist - soll).elements())
                    fehlen = sorted((soll - ist).elements())
                    fehler.append(f"Abgleichtest {name}: unerwartet {zu_viel or '-'}, nicht gefunden {fehlen or '-'}")
            for optionen, schluessel in (((), "exit"), (("--streng",), "exit_streng")):
                rc = cli(pfad, *optionen)
                if rc != erwartet[schluessel]:
                    fehler.append(f"Abgleichtest {name}{' --streng' if optionen else ''}: "
                                  f"Exit-Code {rc}, erwartet {erwartet[schluessel]}")
    return fehler, anzahl


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
    abgleich_fehler, abgleiche = abgleich_pruefen(daten)
    fehler += abgleich_fehler
    raster_fehler, rasterbilder = raster_pruefen()
    fehler += raster_fehler + pfade_pruefen()
    if fehler:
        print("Prüfung fehlgeschlagen:")
        print("\n".join(f"  - {f}" for f in fehler))
        return 1
    print(f"Prüfung bestanden: {anzahl} Kontraste, {len(dateien)} erzeugte Dateien, {len(svgs)} SVGs, "
          f"{abgleiche} Abgleiche, {rasterbilder} Rasterbilder.")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "abgleichen":
        return abgleichen(argv[2:])
    if len(argv) >= 2 and argv[1] == "wortmarke":
        return wortmarke(argv[2:])
    befehle = {"erzeugen": erzeugen, "pruefen": pruefen, "raster": raster}
    if len(argv) != 2 or argv[1] not in befehle:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    return befehle[argv[1]]()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
