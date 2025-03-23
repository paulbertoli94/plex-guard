from fastapi import FastAPI, Request
import uvicorn

from plexguard.TelegramNotificationService import TelegramNotificationService
from plexguard.TorrentCleanerService import TorrentCleanerService

app = FastAPI()

# Inizializza i servizi
torrent_cleaner = TorrentCleanerService()
telegram_notifier = TelegramNotificationService()

@app.post("/downloading")
async def downloading(request: Request):
    data = await request.json()
    torrent_cleaner.clean_torrents()
    return telegram_notifier.process_webhook_data(data)

@app.post("/upgraded")
async def upgraded(request: Request):
    data = await request.json()
    torrent_cleaner.clean_torrents()
    return telegram_notifier.check_language_update(data)

@app.post("/added")
async def added(request: Request):
    data = await request.json()
    torrent_cleaner.clean_torrents()
    return await telegram_notifier.check_language_update(data, True)

if __name__ == "__main__":
    uvicorn.run("plexguard.Controller:app", host="0.0.0.0", port=5001, reload=False)
