import asyncio
import io
import json
import logging
import os
from pathlib import Path

import requests
from plexapi.server import PlexServer
from telegram import Bot

# Configura il logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AUDIO_TRACKS_DB = Path("audio_tracks.json")


class TelegramNotificationService:
    def __init__(self):
        """ Inizializza il servizio di notifica con connessione a Plex e Telegram """
        self.plex_url = os.getenv("PLEX_URL")
        self.plex_token = os.getenv("PLEX_TOKEN")
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.plex = None
        self.bot = None

        # Verifica i parametri e inizializza i servizi
        self._initialize_plex()
        self._initialize_telegram()

    def _initialize_plex(self):
        """ Inizializza la connessione a Plex, se possibile """
        if not self.plex_url or not self.plex_token:
            logger.warning("⚠️ Parametri Plex mancanti: il servizio Plex non sarà attivo.")
            return

        try:
            self.plex = PlexServer(self.plex_url, self.plex_token)
            logger.info("✅ Connessione a Plex avvenuta con successo!")
        except Exception as e:
            logger.error("❌ Errore nella connessione a Plex: %s", e)
            self.plex = None

    def _initialize_telegram(self):
        """ Inizializza il bot Telegram, se possibile """
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.warning("⚠️ Parametri Telegram mancanti: il bot non invierà notifiche.")
            return

        try:
            self.bot = Bot(token=self.telegram_bot_token)
            logger.info("✅ Bot Telegram inizializzato correttamente!")
        except Exception as e:
            logger.error("❌ Errore nell'inizializzazione del bot Telegram: %s", e)
            self.bot = None

    def _find_media_by_imdb_id(self, imdb_id):
        if not self.plex or not imdb_id:
            return None

        logger.info("🔍 Ricerca Plex per imdbId: %s", imdb_id)
        try:
            # Loop su tutte le librerie (es. film, serie, musica...)
            for section in self.plex.library.sections():
                # Considera solo librerie 'movie' o 'show'
                if section.type in ('movie', 'show'):
                    # Ricerca generica (puoi cambiare 'title=""' con year=2021 o altro per limitare i risultati)
                    results = section.search(title="")
                    for item in results:
                        # item.guids potrebbe contenere: ['imdb://tt14039582', 'tmdb://758866', 'tvdb://246288']
                        # Verifichiamo se l'imdbId appare in uno dei GUID
                        if any(f"imdb://{imdb_id}" in g.id for g in item.guids):
                            logger.info("✅ Trovato '%s' con IMDb ID %s nella sezione '%s'",
                                        item.title, imdb_id, section.title)
                            # Forza l'aggiornamento dei metadati per assicurarsi che siano completi
                            item.refresh()
                            item.reload()
                            return item

            logger.warning("⚠️ Nessun risultato trovato per imdbId: %s", imdb_id)
        except Exception as e:
            logger.error("❌ Errore nella ricerca in Plex: %s", e)

        return None

    def _load_audio_db(self):
        try:
            with open(AUDIO_TRACKS_DB, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}  # Se il file è vuoto, ritorna un dizionario vuoto
                return json.loads(content)
        except Exception as e:
            logger.error("❌ Errore nel caricamento del database audio: %s", e)
            return {}

    def _save_audio_db(self, data):
        with open(AUDIO_TRACKS_DB, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def send_telegram_notification(self, title, current_languages, summary, image_url):
        """Invia una notifica su Telegram con messaggio e immagine.

        L'URL dell'immagine viene scaricato e il contenuto viene inviato come file.
        Assicurati che l'URL sia raggiungibile dal server che esegue l'app.
        """
        if not self.bot:
            logger.warning("⚠️ Nessuna connessione Telegram disponibile. Notifica non inviata.")
            return False

        async def _send():
            try:
                # Scarica l'immagine dall'URL
                response = requests.get(image_url)
                if response.status_code != 200:
                    logger.error("❌ Errore nel download dell'immagine: %s", response.status_code)
                    return False

                # Converte il contenuto in un file-like object
                image_bytes = io.BytesIO(response.content)
                image_bytes.name = "image.jpg"  # Imposta un nome per il file (opzionale)

                # Costruisci il messaggio in HTML
                message = f"""<b>{title}</b>
<b>{f"Tracce audio: {', '.join(current_languages)}"}</b>
{summary}

<a href="https://www.youtube.com/results?search_query={title} trailer">Trailer</a>"""

                # Invia la foto con la didascalia
                await self.bot.send_photo(
                    chat_id=self.telegram_chat_id,
                    photo=image_bytes,
                    caption=message,
                    parse_mode="HTML"
                )
                logger.info("📨 Notifica inviata su Telegram con successo!")
                return True
            except Exception as e:
                logger.error("❌ Errore nell'invio della notifica Telegram: %s", e)
                return False

        return asyncio.run(_send())

    def get_media_info(self, media_id):
        """ Recupera informazioni su un film/serie da Plex """
        if not self.plex:
            logger.warning("⚠️ Nessuna connessione a Plex disponibile.")
            return None

        try:
            for media in self.plex.library.all():
                if str(media.ratingKey) == str(media_id):
                    return {
                        "title": media.title,
                        "languages": [track.language for track in media.media[0].parts[0].streams if
                                      track.streamType == 2],
                        "cover": media.thumbUrl
                    }
            logger.warning("⚠️ Media con ID %s non trovato in Plex.", media_id)
            return None
        except Exception as e:
            logger.error("❌ Errore nel recupero dei dati da Plex: %s", e)
            return None

    def process_webhook_data(self, data):
        """Riceve i dati da Sonarr/Radarr al momento del download"""
        imdb_id = data.get('remoteMovie', {}).get('imdbId')
        if not imdb_id:
            logger.warning("⚠️ imdbId mancante nel payload.")
            return "Nessun imdbId"

        media = self._find_media_by_imdb_id(imdb_id)
        if not media:
            return f"Media non trovato su Plex per imdbId {imdb_id}"

        logger.info("Streams trovati: %s", media.media[0].parts[0].streams)

        media_id = str(media.ratingKey)
        media_info = {
            "title": media.title,
            "languages": [track.language for track in media.media[0].parts[0].streams if track.streamType == 2],
            "cover": media.thumbUrl
        }

        audio_db = self._load_audio_db()
        audio_db[media_id] = media_info["languages"]
        self._save_audio_db(audio_db)

        logger.info("🎧 Tracce audio salvate per %s: %s", media_info["title"], media_info["languages"])
        return media_info["languages"]

    def check_language_update(self, data, added=False):
        """Controlla se è stata aggiunta la lingua italiana"""
        imdb_id = data.get('remoteMovie', {}).get('imdbId')
        if not imdb_id:
            logger.warning("⚠️ imdbId mancante nel payload.")
            return "Nessun imdbId"

        media = self._find_media_by_imdb_id(imdb_id)
        if not media:
            return f"Media non trovato su Plex per imdbId {imdb_id}"

        media_id = str(media.ratingKey)
        current_languages = [track.language for track in media.media[0].parts[0].streams if track.streamType == 2]

        audio_db = self._load_audio_db()
        previous_languages = audio_db.get(media_id, [])

        if added:
            self.send_telegram_notification(media.title, current_languages, media.summary, media.thumbUrl)
            return "Notifica aggiunto inviata"
        elif "Italian" in current_languages and "Italian" not in previous_languages:
            self.send_telegram_notification(media.title, current_languages, media.summary, media.thumbUrl)
            return "Notifica italiano inviata"
        else:
            return "Nessun cambiamento rilevante"
