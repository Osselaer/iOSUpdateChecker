#!/usr/bin/env python3
import json, os, smtplib, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, format_datetime

CONFIG = {
    "cache_file": os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_known_version.json"),
    "rss_file":   os.path.join(os.path.dirname(os.path.abspath(__file__)), "feed.xml"),
    "devices": {"iOS": "iPhone18,3"},
    "from_email":    formataddr(("iOS Update Alert", os.environ.get("SMTP_USER", ""))),
    "to_emails":     [os.environ.get("TO_EMAIL", "kosselaer@apple.com")],
    "smtp_host":     "smtp.gmail.com",
    "smtp_port":     587,
    "smtp_user":     os.environ.get("SMTP_USER", ""),
    "smtp_password": os.environ.get("SMTP_PASSWORD", ""),
    "free_user":     os.environ.get("FREE_USER", ""),
    "free_api_key":  os.environ.get("FREE_API_KEY", ""),
    "rss_link":      "https://osselaer.github.io/iOSUpdateChecker/feed.xml",
}

def load_cache():
    if os.path.exists(CONFIG["cache_file"]):
        with open(CONFIG["cache_file"], "r") as f:
            return json.load(f)
    return {}

def save_cache(data):
    with open(CONFIG["cache_file"], "w") as f:
        json.dump(data, f, indent=2)
    print(f"[✓] Cache mis à jour")

def fetch_latest_version(product, device_id):
    url = f"https://api.ipsw.me/v4/device/{device_id}?type=ipsw"
    req = urllib.request.Request(url, headers={"User-Agent": "ios-update-alert/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
            firmwares = data.get("firmwares", [])
            if not firmwares:
                return None
            signed = [f for f in firmwares if f.get("signed", False)] or firmwares
            latest = signed[0]
            return {
                "product": product, "device_id": device_id,
                "version": latest.get("version", "N/A"),
                "build": latest.get("buildid", "N/A"),
                "release_date": latest.get("releasedate", "N/A"),
                "filesize": latest.get("filesize", 0),
            }
    except Exception as e:
        print(f"[✗] Erreur fetch {device_id} : {e}")
        return None

def format_filesize(b):
    if b >= 1_000_000_000: return f"{b/1_000_000_000:.1f} GB"
    if b >= 1_000_000: return f"{b/1_000_000:.0f} MB"
    return f"{b} B"

def format_date(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except:
        return iso

def update_rss(new_versions):
    now = datetime.now(timezone.utc)
    now_rfc822 = format_datetime(now)
    existing_items = ""
    if os.path.exists(CONFIG["rss_file"]):
        with open(CONFIG["rss_file"], "r") as f:
            content = f.read()
            start = content.find("<item>")
            end = content.rfind("</item>")
            if start != -1 and end != -1:
                existing_items = content[start:end + len("</item>")]
    new_items = ""
    for info in new_versions:
        new_items += f"""
    <item>
        <title>iOS {info['version']} ({info['build']})</title>
        <link>https://support.apple.com/en-us/111900</link>
        <guid isPermaLink="false">{info['product']}-{info['version']}-{info['build']}</guid>
        <pubDate>{now_rfc822}</pubDate>
        <description><![CDATA[
            <p><strong>{info['product']} {info['version']}</strong> est disponible.</p>
            <ul>
                <li><strong>Build :</strong> {info['build']}</li>
                <li><strong>Date :</strong> {format_date(info['release_date'])}</li>
                <li><strong>Taille :</strong> {format_filesize(info['filesize'])}</li>
            </ul>
        ]]></description>
    </item>"""
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
    <channel>
        <title>iOS Update Alert</title>
        <link>{CONFIG['rss_link']}</link>
        <description>Alertes mises à jour iOS publiques</description>
        <language>fr-FR</language>
        <lastBuildDate>{now_rfc822}</lastBuildDate>
        <atom:link href="{CONFIG['rss_link']}" rel="self" type="application/rss+xml"/>
        {new_items}
        {existing_items}
    </channel>
</rss>"""
    with open(CONFIG["rss_file"], "w") as f:
        f.write(rss)
    print(f"[✓] Flux RSS mis à jour : feed.xml")

def send_sms(new_versions):
    if not CONFIG["free_user"] or not CONFIG["free_api_key"]:
        print("[!] SMS ignoré : FREE_USER ou FREE_API_KEY manquant")
        return
    summary = ", ".join([f"{v['product']} {v['version']}" for v in new_versions])
    params = urllib.parse.urlencode({"user": CONFIG["free_user"], "pass": CONFIG["free_api_key"], "msg": f"Nouvelle mise a jour : {summary}"})
    try:
        with urllib.request.urlopen(f"https://smsapi.free-mobile.fr/sendmsg?{params}", timeout=10) as r:
            print(f"[✓] SMS envoyé") if r.status == 200 else print(f"[✗] Erreur SMS : {r.status}")
    except Exception as e:
        print(f"[✗] Erreur SMS : {e}")

def send_alert_email(new_versions):
    summary = ", ".join([f"{v['product']} {v['version']}" for v in new_versions])
    rows = "".join([f"<tr><td>{v['product']}</td><td>{v['version']}</td><td>{v['build']}</td><td>{format_date(v['release_date'])}</td><td>{format_filesize(v['filesize'])}</td></tr>" for v in new_versions])
    html = f"<html><body><h2>🍎 {summary}</h2><table border='1'><tr><th>Produit</th><th>Version</th><th>Build</th><th>Date</th><th>Taille</th></tr>{rows}</table><p><a href='{CONFIG['rss_link']}'>Flux RSS</a></p></body></html>"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🍎 Nouvelle mise à jour : {summary}"
    msg["From"] = CONFIG["from_email"]
    msg["To"] = ", ".join(CONFIG["to_emails"])
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(CONFIG["smtp_host"], CONFIG["smtp_port"]) as s:
            s.ehlo(); s.starttls()
            if CONFIG["smtp_user"] and CONFIG["smtp_password"]:
                s.login(CONFIG["smtp_user"], CONFIG["smtp_password"])
            s.sendmail(CONFIG["smtp_user"], CONFIG["to_emails"], msg.as_string())
        print(f"[✓] Email envoyé")
    except Exception as e:
        print(f"[✗] Erreur email : {e}")

def main():
    print(f"\n{'='*52}\n  iOS Update Alert — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n{'='*52}\n")
    cache = load_cache()
    print(f"[i] Cache : {cache if cache else 'vide'}\n")
    new_versions = []
    for product, device_id in CONFIG["devices"].items():
        print(f"[→] Vérification de {product}...")
        info = fetch_latest_version(product, device_id)
        if not info:
            continue
        current = info["version"]
        cached = cache.get(product, {}).get("version")
        print(f"    Version actuelle : {current} | En cache : {cached or 'aucune'}")
        if cached != current:
            print(f"    ✅ NOUVELLE VERSION : {cached or 'N/A'} → {current}\n")
            new_versions.append(info)
            cache[product] = info
        else:
            print(f"    = Pas de changement\n")
    if new_versions:
        print("[!] Envoi des alertes...")
        send_alert_email(new_versions)
        send_sms(new_versions)
        update_rss(new_versions)
        save_cache(cache)
    else:
        print("[✓] Aucune nouvelle mise à jour détectée.")
    print(f"\n{'='*52}\n")

if __name__ == "__main__":
    main()
