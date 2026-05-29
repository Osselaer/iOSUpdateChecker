# 🍎 iOS Update Alert System — Version publique (IPSW.me)

Système de surveillance automatique des mises à jour iOS/iPadOS publiques.
Utilise l'API **IPSW.me** — fonctionne **sans accès au réseau Apple**.

---

## 📁 Structure du projet

```
ios-update-alert/
├── check_ios_update.py              ← Script principal (Python 3)
├── com.apple.ios-update-alert.plist ← LaunchAgent macOS
├── last_known_version.json          ← Cache auto-généré
├── .github/
│   └── workflows/
│       └── ios-alert.yml            ← GitHub Actions (optionnel)
├── logs/
│   ├── output.log
│   └── error.log
└── README.md
```

---

## ⚙️ Configuration

Ouvre `check_ios_update.py` et modifie le bloc `CONFIG` :

```python
CONFIG = {
    # Appareils surveillés par produit (utilise un appareil récent de chaque famille)
    "devices": {
        "iOS":    "iPhone16,2",   # iPhone 15 Pro Max
        "iPadOS": "iPad14,5",     # iPad Pro 12.9" M2
        # "tvOS":  "AppleTV14,1", # Apple TV 4K 3e gen
        # "watchOS": "Watch6,18", # Apple Watch Ultra
    },

    # Destinataires
    "to_emails": ["kosselaer@apple.com"],

    # SMTP (Gmail, Outlook, Apple...)
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "ton.email@gmail.com",
    "smtp_password": "ton_app_password",
}
```

### Trouver un identifiant d'appareil
Consulte : https://www.theiphonewiki.com/wiki/Models
ou l'API : `https://api.ipsw.me/v4/devices`

---

## 🚀 Installation

### Option A — Sur ton Mac (LaunchAgent)

```bash
# 1. Tester manuellement
python3 ~/Documents/ios-update-alert/check_ios_update.py

# 2. Installer le LaunchAgent
cp ~/Documents/ios-update-alert/com.apple.ios-update-alert.plist \
   ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.apple.ios-update-alert.plist

# 3. Vérifier
launchctl list | grep ios-update-alert
```

### Option B — Sur Linux / Raspberry Pi (cron)

```bash
# Copier le projet
scp -r ~/Documents/ios-update-alert/ pi@<ip>:/home/pi/

# Ajouter un cron (toutes les heures)
crontab -e
# Ajouter :
0 * * * * python3 /home/pi/ios-update-alert/check_ios_update.py >> /home/pi/ios-update-alert/logs/output.log 2>&1
```

### Option C — GitHub Actions (recommandé, 24h/24 gratuit)

1. Créer un repo GitHub avec ce projet
2. Aller dans **Settings → Secrets → Actions** et ajouter :
   - `SMTP_USER` → ton email
   - `SMTP_PASSWORD` → ton mot de passe / App Password
   - `TO_EMAIL` → email destinataire
3. Le fichier `.github/workflows/ios-alert.yml` s'occupe du reste ✅

---

## 📧 Configuration SMTP

| Fournisseur | Host | Port | Auth |
|---|---|---|---|
| Gmail | smtp.gmail.com | 587 | App Password |
| Outlook | smtp.office365.com | 587 | Mot de passe |
| Apple (interne) | smtp.apple.com | 587 | Optionnel |

> 💡 Pour Gmail, utilise un **App Password** (pas ton mot de passe principal) :
> Google Account → Sécurité → Mots de passe des applications

---

## 🔧 Dépannage

| Problème | Solution |
|---|---|
| Pas d'email | Vérifier `smtp_user` / `smtp_password` dans CONFIG |
| Erreur réseau | Vérifier la connexion internet |
| Fausses alertes | Supprimer `last_known_version.json` pour réinitialiser |
| Mauvaise version | Changer l'identifiant d'appareil dans `devices` |
