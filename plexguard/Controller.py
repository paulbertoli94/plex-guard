import os

from flask import Flask, jsonify, request

from plexguard.TorrentCleanerService import TorrentCleanerService
from plexguard.TelegramNotificationService import TelegramNotificationService

# Flask App
app = Flask(__name__)

# Inizializza i servizi
torrent_cleaner = TorrentCleanerService()
telegram_notifier = TelegramNotificationService()


@app.route("/clean", methods=["POST"])
def clean_torrents():
    """Webhook di Sonarr: Attiva la pulizia dei torrent"""
    result = torrent_cleaner.clean_torrents()
    return jsonify(result)


@app.route("/downloading", methods=["POST"])
def downloading():
    """Webhook di Sonarr: Notifica il download in corso"""
    data = request.json  # Riceve il JSON dal webhook di Sonarr/Radarr
    result = telegram_notifier.process_webhook_data(data)
    return jsonify({"status": "processed", "result": result})


@app.route("/upgraded", methods=["POST"])
def upgraded():
    """Webhook di Sonarr: Verifica se è stata aggiunta una nuova lingua"""
    data = request.json
    result = telegram_notifier.check_language_update(data)
    return jsonify({"status": "checked", "result": result})

@app.route("/added", methods=["POST"])
def added():
    """Webhook di Sonarr: Verifica se è stata aggiunta una nuova lingua"""
    data = request.json
    result = telegram_notifier.check_language_update(data, True)
    return jsonify({"status": "checked", "result": result})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
