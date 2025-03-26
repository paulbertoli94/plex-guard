import logging
import time

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from plexguard.TelegramNotificationService import TelegramNotificationService
from plexguard.TorrentCleanerService import TorrentCleanerService

logger = logging.getLogger(__name__)

# Inizializza i servizi
torrent_cleaner = TorrentCleanerService()
telegram_notifier = TelegramNotificationService()


async def downloading(request: Request):
    """Webhook di Sonarr: Notifica il download in corso."""
#    body = await request.body()
#    logger.info("REQUEST BODY (raw): %s", body.decode("utf-8"))

    data = await request.json()
    torrent_cleaner.clean_torrents()
    result = telegram_notifier.process_downloading(data)
    return JSONResponse({"status": "OK", "result": result})


async def imported(request: Request):
    """Webhook di Sonarr: Verifica se è stata aggiunta una nuova lingua."""
#    body = await request.body()
#    logger.info("REQUEST BODY (raw): %s", body.decode("utf-8"))

    data = await request.json()
    torrent_cleaner.clean_torrents()
    result = await telegram_notifier.process_imported(data)
    return JSONResponse({"status": "OK", "result": result})


routes = [
    Route("/downloading", endpoint=downloading, methods=["POST"]),
    Route("/imported", endpoint=imported, methods=["POST"]),
]

app = Starlette(debug=False, routes=routes)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)
