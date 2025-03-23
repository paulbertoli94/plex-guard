from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn

from plexguard.TelegramNotificationService import TelegramNotificationService
from plexguard.TorrentCleanerService import TorrentCleanerService

# Inizializza i servizi
torrent_cleaner = TorrentCleanerService()
telegram_notifier = TelegramNotificationService()

async def downloading(request: Request):
    """Webhook di Sonarr: Notifica il download in corso."""
    data = await request.json()
    torrent_cleaner.clean_torrents()
    # Supponendo che process_webhook_data sia sincrono:
    result = telegram_notifier.process_webhook_data(data)
    return JSONResponse({"status": "processed", "result": result})

async def upgraded(request: Request):
    """Webhook di Sonarr: Verifica se è stata aggiunta una nuova lingua."""
    data = await request.json()
    torrent_cleaner.clean_torrents()
    # Supponendo che check_language_update sia sincrono o una coroutine non da awaitare qui:
    result = telegram_notifier.check_language_update(data)
    return JSONResponse({"status": "checked", "result": result})

async def added(request: Request):
    """Webhook di Sonarr: Evento 'added' per segnalare nuovi media."""
    data = await request.json()
    torrent_cleaner.clean_torrents()
    # Se check_language_update è una coroutine, la aspettiamo
    result = await telegram_notifier.check_language_update(data, True)
    return JSONResponse({"status": "checked", "result": result})

routes = [
    Route("/downloading", endpoint=downloading, methods=["POST"]),
    Route("/upgraded", endpoint=upgraded, methods=["POST"]),
    Route("/added", endpoint=added, methods=["POST"]),
]

app = Starlette(debug=False, routes=routes)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)
