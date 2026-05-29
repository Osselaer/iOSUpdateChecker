#!/usr/bin/env python3
"""
iOS Public Update Alert System — Version publique (API IPSW.me)
Surveille les mises à jour iOS/iPadOS publiques via https://api.ipsw.me
et envoie une alerte par email dès qu'une nouvelle version est détectée.

Compatible : macOS, Linux, Raspberry Pi, GitHub Actions
Aucun accès au réseau Apple requis.
"""

import json
import os
import smtplib
import urllib.request
import urllib.error
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ─────────────────────────────────────────────
# CONFIGURATION
# Les valeurs sont lues depuis les variables d'environnement (GitHub Secrets)
# ou depuis les valeurs par défaut ci-dessous.
# ─────────────────────────────────────────────
CONFIG = {
    "cache_file": os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_known_version.json"),

    "devices": {
        "iOS":    "iPhone18,3",   # iPhone 17 Pro
    },

    "from_email":    f"iOS Update Alert <{os.environ.get('SMTP_USER', '')}>",
    "to_emails":    [os.environ.get("TO_EMAIL", "kosselaer@apple.com")],
    "smtp_host":     "smtp.gmail.com",
    "smtp_port":     587,
    "smtp_user":     os.environ.get("SMTP_USER", ""),
    "smtp_password": os.environ.get("SMTP_PASSWORD", ""),
}

# ─────────────────────────────────────────────
# FONCTIONS UTILITAIRES
# ─────────────────────────────────────────────

def load_cache() -> dict:
    if os.path.exists(CONFIG["cache_file"]):
        with open(CONFIG["cache_file"], "r") as f:
            return json.load(f)
    return {}


def save_cache(data: dict):
    with open(CONFIG["cache_file"], "w") as f:
        json.dump(data, f, indent=2)
    print(f"[✓] Cache mis à jour : {CONFIG['cache_file']}")


def fetch_latest_version(product: str, device_id: str) -> dict | None:
    url = f"https://api.ipsw.me/v4/device/{device_id}?type=ipsw"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ios-update-alert/1.0 (python3)",
            "Accept": "application/json",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            firmwares = data.get("firmwares", [])
            if not firmwares:
                print(f"[✗] Aucun firmware trouvé pour {device_id}")
                return None

            signed = [f for f in firmwares if f.get("signed", False)]
            if not signed:
                signed = firmwares

            latest = signed[0]
            return {
                "product":      product,
                "device_id":    device_id,
                "version":      latest.get("version", "N/A"),
                "build":        latest.get("buildid", "N/A"),
                "release_date": latest.get("releasedate", "N/A"),
                "filesize":     latest.get("filesize", 0),
                "url":          latest.get("url", ""),
            }

    except urllib.error.HTTPError as e:
        print(f"[✗] HTTP {e.code} pour {device_id} : {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"[✗] Erreur réseau pour {device_id} : {e.reason}")
        return None
    except json.JSONDecodeError as e:
        print(f"[✗] Erreur JSON pour {device_id} : {e}")
        return None


def format_filesize(size_bytes: int) -> str:
    if size_bytes >= 1_000_000_000:
        return f"{size_bytes / 1_000_000_000:.1f} GB"
    elif size_bytes >= 1_000_000:
        return f"{size_bytes / 1_000_000:.0f} MB"
    return f"{size_bytes} B"


def format_date(iso_date: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return iso_date


def send_alert_email(new_versions: list[dict]):
    now = datetime.now().strftime("%d/%m/%Y à %H:%M")

    rows = ""
    for info in new_versions:
        rows += f"""
        <tr>
            <td style="padding:12px 16px; border-bottom:1px solid #e5e5ea; font-weight:600;">{info['product']}</td>
            <td style="padding:12px 16px; border-bottom:1px solid #e5e5ea; color:#0071e3; font-weight:700; font-size:16px;">{info['version']}</td>
            <td style="padding:12px 16px; border-bottom:1px solid #e5e5ea; font-family:monospace; color:#6e6e73;">{info['build']}</td>
            <td style="padding:12px 16px; border-bottom:1px solid #e5e5ea;">{format_date(info['release_date'])}</td>
            <td style="padding:12px 16px; border-bottom:1px solid #e5e5ea; color:#6e6e73;">{format_filesize(info['filesize'])}</td>
        </tr>
        """

    summary = ", ".join([f"{v['product']} {v['version']}" for v in new_versions])

    html_body = f"""
    <html>
    <body style="margin:0; padding:0; background:#f5f5f7; font-family:-apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif;">
        <div style="max-width:640px; margin:40px auto; background:white; border-radius:20px; overflow:hidden; box-shadow:0 4px 24px rgba(0,0,0,0.08);">
            <div style="background:#1d1d1f; padding:32px; text-align:center;">
                <div style="font-size:48px; margin-bottom:8px;"></div>
                <h1 style="color:white; margin:0; font-size:22px; font-weight:700;">Nouvelle mise à jour détectée</h1>
                <p style="color:#a1a1a6; margin:8px 0 0; font-size:14px;">{summary}</p>
            </div>
            <div style="padding:32px;">
                <p style="color:#6e6e73; font-size:14px; margin-top:0;">
                    Détecté le <strong style="color:#1d1d1f;">{now}</strong> via IPSW.me
                </p>
                <table style="width:100%; border-collapse:collapse; margin-top:16px;">
                    <thead>
                        <tr style="background:#f5f5f7;">
                            <th style="padding:10px 16px; text-align:left; font-size:12px; color:#6e6e73; text-transform:uppercase;">Produit</th>
                            <th style="padding:10px 16px; text-align:left; font-size:12px; color:#6e6e73; text-transform:uppercase;">Version</th>
                            <th style="padding:10px 16px; text-align:left; font-size:12px; color:#6e6e73; text-transform:uppercase;">Build</th>
                            <th style="padding:10px 16px; text-align:left; font-size:12px; color:#6e6e73; text-transform:uppercase;">Date</th>
                            <th style="padding:10px 16px; text-align:left; font-size:12px; color:#6e6e73; text-transform:uppercase;">Taille</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
                <div style="margin-top:28px; padding:20px; background:#f5f5f7; border-radius:12px;">
                    <p style="margin:0 0 10px; font-weight:600; font-size:14px;">🔗 Liens utiles</p>
                    <p style="margin:4px 0; font-size:14px;">📋 <a href="https://support.apple.com/en-us/111900" style="color:#0071e3; text-decoration:none;">Notes de version Apple</a></p>
                    <p style="margin:4px 0; font-size:14px;">📱 <a href="https://developer.apple.com/news/releases/" style="color:#0071e3; text-decoration:none;">Apple Developer Releases</a></p>
            </div>
            <div style="padding:20px 32px; border-top:1px solid #e5e5ea; text-align:center;">
                <p style="margin:0; font-size:12px; color:#a1a1a6;">
                    Envoyé automatiquement par <strong>iOS Update Alert</strong><br>
                    Source : <a href="https://api.ipsw.me" style="color:#0071e3;">api.ipsw.me</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    subject = f" Nouvelle mise à jour publique : {summary}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = CONFIG["from_email"]
    msg["To"]      = ", ".join(CONFIG["to_emails"])
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(CONFIG["smtp_host"], CONFIG["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
            if CONFIG["smtp_user"] and CONFIG["smtp_password"]:
                server.login(CONFIG["smtp_user"], CONFIG["smtp_password"])
            server.sendmail(CONFIG["smtp_user"], CONFIG["to_emails"], msg.as_string())
        print(f"[✓] Email envoyé à : {', '.join(CONFIG['to_emails'])}")
    except Exception as e:
        print(f"[✗] Erreur envoi email : {e}")


# ─────────────────────────────────────────────
# PROGRAMME PRINCIPAL
# ─────────────────────────────────────────────

def main():
    print(f"\n{'='*52}")
    print(f"  iOS Update Alert (IPSW.me) — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*52}\n")

    cache = load_cache()
    print(f"[i] Cache : {cache if cache else 'vide (première exécution)'}\n")

    new_versions = []

    for product, device_id in CONFIG["devices"].items():
        print(f"[→] Vérification de {product} ({device_id})...")
        info = fetch_latest_version(product, device_id)

        if not info:
            print(f"[✗] Impossible de récupérer les infos pour {product}\n")
            continue

        current_version = info["version"]
        cached_version  = cache.get(product, {}).get("version")

        print(f"    Version actuelle : {current_version} ({info['build']})")
        print(f"    Version en cache : {cached_version or 'aucune'}")

        if cached_version != current_version:
            print(f"    ✅ NOUVELLE VERSION : {cached_version or 'N/A'} → {current_version}\n")
            new_versions.append(info)
            cache[product] = info
        else:
            print(f"    = Pas de changement\n")

    if new_versions:
        print("[!] Envoi de l'alerte email...")
        send_alert_email(new_versions)
        save_cache(cache)
    else:
        print("[✓] Aucune nouvelle mise à jour détectée.")

    print(f"\n{'='*52}\n")


if __name__ == "__main__":
    main()
