#!/usr/bin/env python3
"""Vergleicht, was die WinUI-Probe ausgibt, mit den Tokens.

    python3 tests/winui/vergleichen.py ORDNER    (darin hell.json, dunkel.json, kontrast.json)
"""
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "werkzeuge"))
import marke  # noqa: E402

daten = marke.laden()
reihe = marke.akzentreihe(daten)
ordner = Path(sys.argv[1])
fehler: list[str] = []


def argb(farbe: str) -> str:
    return "#FF" + farbe[1:].upper()


def als_float32(x: str) -> float | None:
    try:
        return struct.unpack("f", struct.pack("f", float(x)))[0]
    except (TypeError, ValueError, OverflowError):
        return None


def gleich(ist: str | None, wert: str) -> bool:
    """Gleich als Text oder als Zahl. WinUI liest x:Double hier mit der Genauigkeit von float:
    35.2 kommt als 35.20000076293945 zurueck. Verglichen wird deshalb auf float gerundet."""
    if ist == wert:
        return True
    a, b = als_float32(ist), als_float32(wert)
    return a is not None and a == b


def soll(name: str, ist: dict, schluessel: str, wert: str) -> None:
    if not gleich(ist.get(schluessel), wert):
        fehler.append(f"{name}: {schluessel} ist {ist.get(schluessel)}, soll {wert}")


for name, thema in (("hell", "hell"), ("dunkel", "dunkel")):
    ist = json.loads((ordner / f"{name}.json").read_text(encoding="utf-8"))
    for f in daten["farben"]:
        n, w = marke.pascal(f["rolle"]), argb(daten["wert"][thema][f["rolle"]])
        for k in (f"Fs{n}Color", f"Fs{n}Brush", f"ui:Fs{n}Brush"):
            soll(name, ist, k, w)
    for stufe, farbe in reihe.items():
        soll(name, ist, stufe, argb(farbe))
    nutzung = marke.WINUI_NUTZUNG[thema]
    soll(name, ist, "AccentFillColorDefaultBrush", argb(reihe[nutzung["flaeche"]]))
    soll(name, ist, "AccentTextFillColorPrimaryBrush", argb(reihe[nutzung["text"][0]]))
    soll(name, ist, "ControlCornerRadius", daten["form"]["radius"])
    soll(name, ist, "FsFocusThickness", marke.ohne_px(daten["form"]["fokus-staerke"]))
    for k, v in daten["schrift"].items():
        soll(name, ist, f"FsFont{marke.pascal(k)}", v["xaml"])
    for s in daten["groessen"]["stufen"]:
        soll(name, ist, f"FsGroesse{marke.pascal(s['rolle'])}", marke.px(s["wert"]))
    for a in daten["abstaende"]:
        soll(name, ist, f"FsAbstand{a['stufe']}", marke.px(a["wert"]))
    soll(name, ist, "FsStaerkeUeberschrift", daten["satz"]["staerke-ueberschrift"])

ist = json.loads((ordner / "kontrast.json").read_text(encoding="utf-8"))
for rolle, system in daten["winui"]["hoher-kontrast"].items():
    n, w = marke.pascal(rolle), ist.get(system)
    if not w or w == "<fehlt>":
        fehler.append(f"kontrast: Systemfarbe {system} fehlt")
        continue
    for k in (f"Fs{n}Color", f"Fs{n}Brush", f"ui:Fs{n}Brush"):
        soll("kontrast", ist, k, w)

if fehler:
    print("WinUI-Probe weicht ab:")
    print("\n".join(f"  - {f}" for f in fehler))
    sys.exit(1)
print(f"WinUI-Probe passt: {len(daten['farben'])} Rollen in hell, dunkel und hohem Kontrast, Akzentreihe greift.")
