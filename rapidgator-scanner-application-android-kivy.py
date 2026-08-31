#!/usr/bin/env python3
"""
Rapidgator Link Scanner - Version Android (Kivy)
------------------------------------------------
Application Android native utilisant Kivy pour l'interface et le module urllib
pour le scraping et la verification des liens rapidgator.net.

Principe :
  - Un lien valide reste sur son URL d'origine (page de telechargement)
  - Un lien expire redirige vers https://rapidgator.net/article/premium

Auteur : Genere pour Alexandre BOULANGER
"""

import os
import re
import threading
import urllib.parse
import urllib.request
import urllib.error

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.metrics import dp

# --- Configuration ---

EXPIRED_REDIRECT = "rapidgator.net/article/premium"

# Regex pour identifier les liens rapidgator.net
RAPIDGATOR_REGEX = re.compile(
    r'https?://(?:www\.)?rapidgator\.net/file/[a-zA-Z0-9_]+(?:/[^\s"\'<>]*)?\.html',
    re.IGNORECASE
)

# Chemin de sortie adapte a Android
OUTPUT_FILE = os.path.join(os.path.expanduser("~"), "liens_valides.txt")


def fetch_page(url):
    """Recupere le contenu HTML d'une page web."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1")


def extract_rapidgator_links(html):
    """Extrait et dedoublonne les liens rapidgator.net d'un contenu HTML."""
    links = set(RAPIDGATOR_REGEX.findall(html))
    normalized = set()
    for link in links:
        link = link.split("#")[0]
        if link:
            normalized.add(link.strip())
    return normalized


def check_link(link_url):
    """
    Verifie la validite d'un lien rapidgator en testant sa redirection HTTP.
    Retourne True si valide, False si expire ou en erreur.
    """
    req = urllib.request.Request(
        link_url,
        method="HEAD",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        },
    )

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    try:
        response = opener.open(req, timeout=15)
        return True
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            location = e.headers.get("Location", "")
            if EXPIRED_REDIRECT in location:
                return False
            return True
        return False
    except Exception:
        return False


def write_output_file(valid_links, output_path):
    """Ecrit les liens valides dans un fichier texte, tries alphabetiquement."""
    sorted_links = sorted(valid_links)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Liens Rapidgator valides - generes par Rapidgator Scanner\n")
        f.write(f"# Total : {len(sorted_links)} lien(s) valide(s)\n")
        f.write("#\n")
        for link in sorted_links:
            f.write(link + "\n")
    return len(sorted_links)


class ScannerApp(App):
    """Application Kivy principale."""

    def build(self):
        self.title = "Rapidgator Scanner"
        self.scanning = False
        self.valid_links = []

        layout = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))

        # Titre
        self.title_label = Label(
            text="Rapidgator Link Scanner",
            font_size=dp(22),
            size_hint_y=None,
            height=dp(40),
            bold=True,
        )
        layout.add_widget(self.title_label)

        self.subtitle_label = Label(
            text="Verification de validite par redirection HTTP",
            font_size=dp(12),
            size_hint_y=None,
            height=dp(20),
            color=(0.5, 0.5, 0.5, 1),
        )
        layout.add_widget(self.subtitle_label)

        # Champ URL
        layout.add_widget(Label(
            text="URL du site a scanner :",
            font_size=dp(13),
            size_hint_y=None,
            height=dp(25),
            halign="left",
            valign="middle",
        ))

        self.url_input = TextInput(
            hint_text="https://www.example.com/page-avec-liens",
            font_size=dp(14),
            size_hint_y=None,
            height=dp(45),
            multiline=False,
        )
        layout.add_widget(self.url_input)

        # Bouton scan
        self.scan_btn = Button(
            text="Lancer le scan",
            font_size=dp(15),
            size_hint_y=None,
            height=dp(50),
            background_color=(0.91, 0.27, 0.38, 1),
        )
        self.scan_btn.bind(on_press=self.on_scan)
        layout.add_widget(self.scan_btn)

        # Barre de progression
        self.progress_bar = ProgressBar(
            size_hint_y=None,
            height=dp(15),
            value=0,
        )
        layout.add_widget(self.progress_bar)

        # Label de statut
        self.status_label = Label(
            text="En attente...",
            font_size=dp(12),
            size_hint_y=None,
            height=dp(25),
            color=(0.5, 0.5, 0.5, 1),
            halign="left",
            valign="middle",
        )
        layout.add_widget(self.status_label)

        # Stats
        self.stats_label = Label(
            text="Liens trouves : 0 | Valides : 0 | Invalides : 0",
            font_size=dp(13),
            size_hint_y=None,
            height=dp(30),
            halign="left",
            valign="middle",
        )
        layout.add_widget(self.stats_label)

        # Zone de resultats (scrollable)
        self.results_scroll = ScrollView(size_hint_y=1)
        self.results_label = Label(
            text="",
            font_size=dp(11),
            valign="top",
            halign="left",
            text_size=(None, None),
            size_hint_y=None,
            markup=True,
        )
        self.results_label.bind(
            width=lambda *x: self.results_label.setter("text_size")(self.results_label, (self.results_label.width, None))
        )
        self.results_scroll.add_widget(self.results_label)
        layout.add_widget(self.results_scroll)

        # Bouton sauvegarde
        self.save_btn = Button(
            text="Sauvegarder les liens valides",
            font_size=dp(14),
            size_hint_y=None,
            height=dp(45),
            background_color=(0.18, 0.80, 0.44, 1),
            disabled=True,
        )
        self.save_btn.bind(on_press=self.on_save)
        layout.add_widget(self.save_btn)

        return layout

    def on_scan(self, instance):
        if self.scanning:
            return

        url = self.url_input.text.strip()
        if not url:
            self.status_label.text = "Veuillez saisir une URL."
            return

        self.scanning = True
        self.scan_btn.disabled = True
        self.scan_btn.text = "Scan en cours..."
        self.progress_bar.value = 0
        self.status_label.text = "Recuperation de la page..."
        self.stats_label.text = "Liens trouves : 0 | Valides : 0 | Invalides : 0"
        self.results_label.text = ""
        self.save_btn.disabled = True
        self.valid_links = []

        thread = threading.Thread(target=self._run_scan, args=(url,), daemon=True)
        thread.start()

    def _run_scan(self, target_url):
        """Execute le scan dans un thread dedie."""
        try:
            html = fetch_page(target_url)
            links = extract_rapidgator_links(html)
            total = len(links)

            if not links:
                Clock.schedule_once(lambda dt: self._update_status("Termine : aucun lien trouve.", 100))
                Clock.schedule_once(lambda dt: self._scan_finished())
                return

            Clock.schedule_once(lambda dt: self._update_status(f"{total} liens trouves. Verification en cours...", 0))

            valid_count = 0
            invalid_count = 0
            results_text = ""

            for i, link in enumerate(sorted(links)):
                is_valid = check_link(link)
                if is_valid:
                    valid_count += 1
                    self.valid_links.append(link)
                    results_text += f"[color=2ecc71][+] {link}[/color]\n"
                else:
                    invalid_count += 1
                    results_text += f"[color=e74c3c][-] {link}[/color]\n"

                progress = int((i + 1) / total * 100)
                status = f"Verification {i + 1}/{total}..."
                stats = f"Liens trouves : {total} | Valides : {valid_count} | Invalides : {invalid_count}"

                Clock.schedule_once(
                    lambda dt, s=status, p=progress, st=stats, r=results_text:
                    self._update_progress(s, p, st, r)
                )

            Clock.schedule_once(
                lambda dt: self._update_status(
                    f"Termine : {valid_count} valide(s) sur {total}.", 100
                )
            )

        except urllib.error.URLError as e:
            Clock.schedule_once(
                lambda dt: self._update_status(f"Erreur : {e.reason}", 0)
            )
        except Exception as e:
            Clock.schedule_once(
                lambda dt: self._update_status(f"Erreur : {str(e)}", 0)
            )
        finally:
            Clock.schedule_once(lambda dt: self._scan_finished())

    def _update_status(self, text, progress):
        self.status_label.text = text
        self.progress_bar.value = progress

    def _update_progress(self, status, progress, stats, results):
        self.status_label.text = status
        self.progress_bar.value = progress
        self.stats_label.text = stats
        self.results_label.text = results

    def _scan_finished(self):
        self.scanning = False
        self.scan_btn.disabled = False
        self.scan_btn.text = "Lancer le scan"
        if self.valid_links:
            self.save_btn.disabled = False

    def on_save(self, instance):
        if not self.valid_links:
            return
        try:
            count = write_output_file(self.valid_links, OUTPUT_FILE)
            self.status_label.text = f"{count} lien(s) sauvegarde(s) dans {OUTPUT_FILE}"
        except Exception as e:
            self.status_label.text = f"Erreur lors de la sauvegarde : {str(e)}"


if __name__ == "__main__":
    ScannerApp().run()


"""
=== FICHIER buildozer.spec (a placer dans le meme dossier que main.py) ===

[app]

# Application metadata
title = Rapidgator Scanner
package.name = rapidgatorscanner
package.domain = org.rapidgator.scanner

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt

version = 1.0.0

# Requirements - Kivy and standard library only
requirements = python3,kivy

# Android configuration
orientation = portrait

# Android permissions
android.permissions = INTERNET

# Android API settings
android.api = 31
android.minapi = 21
android.sdk = 31
android.ndk = 23b

# Build settings
fullscreen = 0

# Log settings
log_level = 2

# Android architecture - build for ARM (most devices) and ARM64
android.archs = arm64-v8a, armeabi-v7a

# Allow backup
android.allow_backup = 1


[buildozer]

log_level = 2
warn_on_root = 1

=== FIN DU FICHIER buildozer.spec ===


Le guide de compilation complet (methode GitHub Actions + methode locale)
se trouve dans le canvas "Guide de compilation APK - Rapidgator Scanner Android".
"""