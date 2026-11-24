"""marke.py meldet fehlende Logos und Quellen als Befund statt mit einem Traceback (#9).

Jeder Fall prüft eine Kopie des Repos, in der genau eine Datei fehlt, und ruft marke.py dort als eigenen Prozess
auf, so wie die CI es tut. Erwartet wird Exitcode 1, eine Zeile „fehlt: <datei>“ und kein Traceback.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]


class FehlendeDatei(unittest.TestCase):

    def lauf_ohne(self, rel: str, befehl: str = "pruefen") -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as tmp:
            kopie = Path(tmp) / "marke"
            shutil.copytree(WURZEL, kopie, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            (kopie / rel).unlink()
            return subprocess.run([sys.executable, "-I", str(kopie / "werkzeuge" / "marke.py"), befehl],
                                  capture_output=True, text=True, timeout=300)

    def erwarte_befund(self, lauf: subprocess.CompletedProcess, rel: str) -> None:
        ausgabe = lauf.stdout + lauf.stderr
        self.assertNotIn("Traceback", ausgabe)
        self.assertEqual(lauf.returncode, 1, ausgabe)
        self.assertIn(f"fehlt: {rel}", ausgabe)

    def test_logos_mit_pfaden(self):
        for rel in ("logos/firestrike-logo-light.svg", "logos/firestrike-logo-dark.svg"):
            with self.subTest(rel=rel):
                lauf = self.lauf_ohne(rel)
                self.erwarte_befund(lauf, rel)
                self.assertIn("wortmarke", lauf.stdout)
                # Erzeugen meldet dasselbe, statt abzubrechen, ohne zu sagen warum.
                self.erwarte_befund(self.lauf_ohne(rel, "erzeugen"), rel)

    def test_fassung_mit_text(self):
        rel = "logos/quellen/firestrike-logo-light-text.svg"
        self.erwarte_befund(self.lauf_ohne(rel), rel)

    def test_quelle_der_rasterbilder(self):
        rel = "logos/firestrike-symbol.svg"
        lauf = self.lauf_ohne(rel)
        self.erwarte_befund(lauf, rel)
        # einmal, nicht für jedes der Rasterbilder
        self.assertEqual(lauf.stdout.count(f"fehlt: {rel}, die Quelle der Rasterbilder"), 1, lauf.stdout)


if __name__ == "__main__":
    unittest.main()
