# 🎬 PlexGuard

**PlexGuard** è un'app Flask che:
- elimina automaticamente torrent completati da qBittorrent in base a regole personalizzabili,
- si integra con **Plex** per monitorare le lingue disponibili dei contenuti,
- invia notifiche via **Telegram** quando viene rilevata l'aggiunta della lingua italiana.

Pensato per chi usa **Sonarr/Radarr** con Plex e vuole mantenere una libreria pulita e aggiornata.

---

## 🚀 Funzionalità

- ✅ Elimina automaticamente i torrent:
  - senza commento ✅ subito
  - con commento ✅ solo se più vecchi di `N` giorni
- 🔁 Riceve webhook da **Sonarr/Radarr**
- 🧠 Controlla da **Plex** le lingue disponibili di un film/serie
- 🇮🇹 Invia una notifica **Telegram** se viene aggiunta la lingua italiana
- 📦 Completamente **containerizzato con Docker**
- ⚙️ Configurabile via **variabili d'ambiente** o `.env`

---

## 📦 Requisiti

- Python 3.12 **(se usato localmente)**  
- Docker **(raccomandato)**
- qBittorrent con API attive
- Sonarr o Radarr configurato con webhook
- Plex Media Server
- Bot Telegram

---

## 🛠️ Installazione

### 1. Clona il repository

```bash
git clone https://github.com/tuo-username/plexguard.git
cd plexguard
```

### 2. Crea il file `.env`

```env
QBITTORRENT_URL=http://192.168.1.10:8080
QBITTORRENT_USER=admin
QBITTORRENT_PASS=password
DAYS_OLD=60

PLEX_URL=http://192.168.1.13:32400
PLEX_TOKEN=PLEX-TOKEN

TELEGRAM_BOT_TOKEN=123456789:ABCDefghIjkLmNopQRstuVwxyZ
TELEGRAM_CHAT_ID=123456789
```

### 3. Build & Run con Docker

```bash
docker build -t plexguard .
docker run -d -p 5001:5001 --env-file .env --name plexguard -v ${PWD}/audio_tracks.json:/app/audio_tracks.json plexguard
```

---

## 🧩 Integrazione con Sonarr/Radarr

1. Vai su **Settings > Connect > Add > Webhook**
2. Inserisci:
   - **URL:** `http://<IP_DEL_SERVER>:5001/downloading`
   - **Eventi:** `On File Import`, `On File Upgrade`, `On Import Complete`
3. Crea un secondo webhook (per l’import finale):
   - **URL:** `http://<IP_DEL_SERVER>:5001/imported`
   - **Eventi:** `On Import Complete` **(solo)**

---

## 🔍 Test locali

Verifica se l'app è attiva:

```bash
curl -X POST http://localhost:5001/downloading -H "Content-Type: application/json" -d '{}'
```

Vedi i log del container:

```bash
docker logs -f plexguard
```

---

## ⚙ Personalizzazione

- Puoi cambiare la logica di eliminazione modificando `TorrentCleanerService.py`
- Puoi modificare le notifiche Telegram da `TelegramNotificationService.py`
- Supporto a `Radarr`, `Lidarr`, `Readarr` facilmente integrabile.

---

## 📁 Struttura progetto

```
plexguard/
├── Controller.py               # Webhook Flask
├── TorrentCleanerService.py   # Pulizia torrent da qBittorrent
├── TelegramNotificationService.py  # Integrazione Plex + Telegram
├── __init__.py
requirements.txt
Dockerfile
.env.example
```

---

## ✨ Autore

**Tuo Nome** – [GitHub](https://github.com/tuo-username)

Se ti piace il progetto, lascia una ⭐ su GitHub!
