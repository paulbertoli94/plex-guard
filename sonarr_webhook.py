from flask import Flask, jsonify
import requests
import datetime
import os

# Legge le credenziali dall'ambiente
QBITTORRENT_URL = os.getenv("QBITTORRENT_URL")
USERNAME = os.getenv("QBITTORRENT_USER")
PASSWORD = os.getenv("QBITTORRENT_PASS")
DAYS_OLD = int(os.getenv("DAYS_OLD"))

# Flask App
app = Flask(__name__)

def login_qbittorrent():
    """ Effettua il login a qBittorrent e restituisce una sessione autenticata """
    session = requests.Session()
    login_data = {"username": USERNAME, "password": PASSWORD}
    response = session.post(f"{QBITTORRENT_URL}/api/v2/auth/login", data=login_data)
    if response.text == "Ok.":
        return session
    print("❌ Errore di login su qBittorrent")
    return None

def delete_torrent(session, torrent_hash, delete_files=True):
    """ Elimina un torrent per hash """
    response = session.post(
        f"{QBITTORRENT_URL}/api/v2/torrents/delete",
        data={"hashes": torrent_hash, "deleteFiles": "true" if delete_files else "false"}
    )
    return response.status_code == 200

def clean_torrents():
    """ Controlla i torrent e applica le regole di eliminazione """
    session = login_qbittorrent()
    if not session:
        return {"status": "error", "message": "Impossibile connettersi a qBittorrent"}

    response = session.get(f"{QBITTORRENT_URL}/api/v2/torrents/info")
    if response.status_code != 200:
        return {"status": "error", "message": "Errore nel recupero dei torrent"}

    torrents = response.json()
    deleted_count = 0
    now = datetime.datetime.now()

    for torrent in torrents:
        torrent_hash = torrent["hash"]
        added_on = datetime.datetime.fromtimestamp(torrent["added_on"])
        days_old = (now - added_on).days
        comment = torrent.get("comment", "").strip()

        # Controlla se il torrent è completo
        if torrent["progress"] < 1.0:
            print(f"⏳ Torrent '{torrent['name']}' ancora in download ({torrent['progress'] * 100:.2f}%), skip.")
            continue  # ⬅️ Salta direttamente al prossimo torrent

        if not comment or comment == "dynamic metainfo from client":
            print(f"🚮 Eliminando torrent senza commento: valido{torrent['name']}")
            if delete_torrent(session, torrent_hash):
                deleted_count += 1
        elif days_old > DAYS_OLD:
            print(f"📅 Eliminando torrent '{torrent['name']}' con commento (aggiunto {days_old} giorni fa)")
            if delete_torrent(session, torrent_hash):
                deleted_count += 1

    return {"status": "success", "deleted": deleted_count}

@app.route("/webhook", methods=["POST"])
def webhook():
    """ Webhook di Sonarr: Attiva la pulizia dei torrent """
    result = clean_torrents()
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
