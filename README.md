# qBittorrent Torrent Cleaner

qBittorrent Torrent Cleaner è un'app Flask che elimina automaticamente i torrent in base a determinate condizioni, utilizzando un webhook da Sonarr.

## 🛠️ Funzionalità
- ✅ Elimina i torrent **senza commento** immediatamente.
- ⏳ Elimina i torrent **con commento solo se più vecchi di 60 giorni**.
- 🚀 Si integra con **Sonarr** tramite webhook.
- 🛠️ Funziona in **Docker** per una facile gestione.
- 🛡️ Usa **variabili d'ambiente** per la configurazione.

---

## ✅ Requisiti
- **Docker** (se vuoi eseguire l'app in container)
- **Python 3.12** (se vuoi eseguire lo script manualmente)
- **qBittorrent** con API attive
- **Sonarr** per inviare il webhook

---

## 🛠️ Installazione

### **1. Clonare il repository**
```bash
git clone https://github.com/tuo-username/torrent-cleaner.git
cd torrent-cleaner
```

### **2. Creare il file `.env` per la configurazione**
Crea un file `.env` nella cartella principale e inserisci le credenziali per qBittorrent:

```
QBITTORRENT_URL=http://192.168.1.1:8080
QBITTORRENT_USER=admin
QBITTORRENT_PASS=mypassword
```

### **3. Build ed Esecuzione con Docker**
```bash
docker build -t torrent-cleaner .
docker run -d -p 5001:5001 --env-file .env --name torrent-cleaner torrent-cleaner
```

Oppure, se usi `docker-compose.yml`, avvia con:
```bash
docker-compose up -d
```

---

## 💾 Configurazione di Sonarr

1. **Vai su Sonarr** → **Settings** → **Connect**.
2. **Aggiungi un Webhook**.
3. **URL:** `http://IP_DEL_SERVER:5000/webhook`
4. **Attiva solo "On Import"**.
5. **Salva** e prova un episodio per verificare che funzioni.

---

## ✅ Test e Debug

Per verificare che il server sia attivo, esegui:
```bash
curl -X POST http://127.0.0.1:5000/webhook
```
Se tutto funziona, otterrai:
```json
{"status": "success", "message": "Webhook ricevuto!"}
```

Per vedere i log del container:
```bash
docker logs torrent-cleaner
```

---

## ⚙ Personalizzazioni
- Modifica il numero di giorni prima dell'eliminazione (attualmente **60 giorni**).
- Aggiungi notifiche Telegram o log su file.
- Integra altri client come Radarr o Lidarr.

---

## 🌟 Autore
**Tuo Nome** - [GitHub](https://github.com/tuo-username)

Se trovi utile questo progetto, lascia una ⭐ su GitHub!

