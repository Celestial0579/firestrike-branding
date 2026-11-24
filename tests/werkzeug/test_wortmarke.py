"""pruefen bindet die Logos mit Pfaden an das, was `marke.py wortmarke` erzeugt hat (#18).

Jeder Fall ändert eine Kopie des Repos so, wie es von Hand passieren könnte, und ruft `marke.py pruefen` dort als
eigenen Prozess auf. Eine Schrift braucht keiner der Fälle.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]
DUNKEL = "logos/firestrike-logo-dark.svg"
DUNKEL_TEXT = "logos/quellen/firestrike-logo-dark-text.svg"
HELL_TEXT = "logos/quellen/firestrike-logo-light-text.svg"
QUELLE = "logos/quellen/quelle.json"


class WortmarkeGebunden(unittest.TestCase):

    def pruefen_nach(self, aendern, erzeugen: bool = False) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as tmp:
            kopie = Path(tmp) / "marke"
            shutil.copytree(WURZEL, kopie, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            aendern(kopie)
            marke = [sys.executable, "-I", str(kopie / "werkzeuge" / "marke.py")]
            if erzeugen:
                subprocess.run([*marke, "erzeugen"], check=True, capture_output=True, timeout=300)
            return subprocess.run([*marke, "pruefen"], capture_output=True, text=True, timeout=300)

    def test_von_hand_verschobene_wortmarke(self):
        """Der Fall aus #18: Wortmarke im dunklen Logo um 3 Einheiten verschoben, die einfarbige Fassung neu erzeugt."""
        def verschieben(kopie: Path) -> None:
            datei = kopie / DUNKEL
            text = datei.read_text(encoding="utf-8")
            pfade = list(re.finditer(r'<path d="M([0-9.]+)', text))
            letzter = pfade[-1]   # die Wortmarke steht nach dem Zeichen
            neu = f'<path d="M{float(letzter.group(1)) + 3:g}'
            datei.write_text(text[:letzter.start()] + neu + text[letzter.end():], encoding="utf-8")
        lauf = self.pruefen_nach(verschieben, erzeugen=True)
        self.assertEqual(lauf.returncode, 1, lauf.stdout)
        self.assertIn(f"verändert: {DUNKEL} ist nicht mehr, was wortmarke erzeugt hat", lauf.stdout)

    def test_fassungen_mit_text_laufen_auseinander(self):
        def laufweite(kopie: Path) -> None:
            datei = kopie / DUNKEL_TEXT
            text = datei.read_text(encoding="utf-8")
            self.assertIn('letter-spacing="2.6"', text)
            datei.write_text(text.replace('letter-spacing="2.6"', 'letter-spacing="3"'), encoding="utf-8")
        lauf = self.pruefen_nach(laufweite)
        self.assertEqual(lauf.returncode, 1, lauf.stdout)
        self.assertIn(f"Wortmarke: {DUNKEL_TEXT} weicht von {HELL_TEXT} ab (letter-spacing)", lauf.stdout)

    def test_liste_ohne_pruefsummen_der_logos(self):
        def alte_liste(kopie: Path) -> None:
            datei = kopie / QUELLE
            liste = json.loads(datei.read_text(encoding="utf-8"))
            del liste["logos"]
            datei.write_text(json.dumps(liste, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        lauf = self.pruefen_nach(alte_liste)
        self.assertEqual(lauf.returncode, 1, lauf.stdout)
        self.assertIn(f"veraltet: {QUELLE} ohne Prüfsummen der Logos", lauf.stdout)

    def test_unveraendert_bestanden(self):
        lauf = self.pruefen_nach(lambda kopie: None)
        self.assertEqual(lauf.returncode, 0, lauf.stdout)


if __name__ == "__main__":
    unittest.main()
