import io
import json
import logging
import os
import time
from pathlib import Path

import requests
from plexapi.server import PlexServer
from telegram import Bot

# Configura il logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AUDIO_TRACKS_DB = Path("audio_tracks.json")

# Mappatura delle lingue alle emoji delle bandiere
flag_mapping = {
    "Italian": "🇮🇹",
    "English": "🇺🇸",  # per l'inglese, usa la bandiera degli USA
    "Giapponese": "🇯🇵",
    "Japanese": "🇯🇵",
    "French": "🇫🇷",
    "Spanish": "🇪🇸",
    "German": "🇩🇪",
    "Russian": "🇷🇺",
    "Korean": "🇰🇷",
    "Chinese": "🇨🇳",
    "Hindi": "🇮🇳",
    "Portuguese": "🇵🇹",
    "Arabic": "🇸🇦",
    "Turkish": "🇹🇷",
    "Vietnamese": "🇻🇳",
    "Polish": "🇵🇱",
    "Dutch": "🇳🇱",
    "Swedish": "🇸🇪",
    "Norwegian": "🇳🇴",
    "Finnish": "🇫🇮",
    "Greek": "🇬🇷",
    "Hebrew": "🇮🇱",
    "Thai": "🇹🇭",
    "Indonesian": "🇮🇩",
    "Malay": "🇲🇾",
    "Czech": "🇨🇿",
    "Romanian": "🇷🇴",
    "Hungarian": "🇭🇺"
}


def get_episode_unique_imdb_id(data):
    """
    Crea un identificatore univoco per un episodio combinando l'IMDb ID, il numero di stagione e di episodio.
    Se uno di questi campi manca, restituisce solo l'IMDb ID come fallback.
    """
    imdb_id = data.get("series", {}).get("imdbId")
    season_number = data.get("episode", {}).get("seasonNumber")
    episode_number = data.get("episode", {}).get("episodeNumber")

    if imdb_id and season_number is not None and episode_number is not None:
        # Formatta la stagione e l'episodio con due cifre (es. S01E01)
        return f"{imdb_id}-S{int(season_number):02d}E{int(episode_number):02d}"
    return imdb_id  # fallback se non tutti i dati sono disponibili


def _load_audio_db():
    try:
        with open(AUDIO_TRACKS_DB, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}  # Se il file è vuoto, ritorna un dizionario vuoto
            return json.loads(content)
    except Exception as e:
        logger.error("❌ Errore nel caricamento del database audio: %s", e)
        return {}


def _save_audio_db(data):
    with open(AUDIO_TRACKS_DB, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


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

    def _find_media_by_id(self, data):
        if not self.plex:
            return None

        if data.get('movie'):
            imdb_id = data.get('movie').get('imdbId')
            logger.info("🔍 Ricerca Plex per imdb_id: %s", imdb_id)
            for section in self.plex.library.sections():
                if section.type == 'movie':
                    results = section.search(title="")
                    for item in results:
                        if any(f"imdb://{imdb_id}" in g.id for g in item.guids):
                            logger.info("✅ Trovato '%s' con tvdb ID %s nella sezione '%s'",
                                        item.title, imdb_id, section.title)
                            item.refresh()
                            item.reload()
                            return item, imdb_id

        if data.get('series'):
            tvdb_id = data.get('series').get('tvdbId')
            logger.info("🔍 Ricerca Plex per tvdbId: %s", tvdb_id)
            for section in self.plex.library.sections():
                if section.type == 'show':
                    results = section.search(title="")
                    for item in results:
                        if any(f"tvdb://{tvdb_id}" in g.id for g in item.guids):
                            logger.info("✅ Trovato '%s' con tvdb ID %s nella sezione '%s'",
                                        item.title, tvdb_id, section.title)
                            item.refresh()
                            item.reload()
                            return item, tvdb_id

        return None, None

    async def send_telegram_notification(self, title, current_languages, summary, image_url):
        """Invia una notifica su Telegram con messaggio e immagine.

        L'URL dell'immagine viene scaricato e inviato come file.
        Questa funzione è interamente asincrona e deve essere chiamata con `await`.
        """
        if not self.bot:
            logger.warning("⚠️ Nessuna connessione Telegram disponibile. Notifica non inviata.")
            return False

        try:
            # Scarica l'immagine dall'URL in modo sincrono
            # (Se vuoi farlo asincrono puoi usare aiohttp, ma qui restiamo semplici)
            response = requests.get(image_url)
            if response.status_code != 200:
                logger.error("❌ Errore nel download dell'immagine: %s", response.status_code)
                return False

            # Converte il contenuto in un file-like object
            image_bytes = io.BytesIO(response.content)
            image_bytes.name = "image.jpg"  # Nome del file (opzionale)

            # Sostituisci ogni lingua con la sua emoji (se disponibile)
            flags = [flag_mapping.get(lang, lang) for lang in current_languages]

            message = (
                f"<b>{title}</b>\n"
                f"<b>Tracce audio: {', '.join(flags)}</b>\n"
                f"{summary}\n\n"
                f'<a href="https://www.youtube.com/results?search_query={title} trailer">Trailer</a>'
            )

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

    def get_languages(self, data):
        """
        Restituisce una tupla (media, languages, id) dove:
          - media: l'oggetto media (film o episodio)
          - languages: lista deduplicata delle lingue audio
          - id: identificatore univoco per l'elemento
        """
        logger.info("DATA: %s", data)
        media, id = self._find_media_by_id(data)
        if not media:
            return None, None, None

        # Se il media è una serie, costruisci un ID univoco per l'episodio
        if media.type == "show" and media.episodes():
            episodes = media.episodes()
            episode_tvdb_id = max(data.get('episodes', []), key=lambda ep: ep.get("tvdbId", 0)).get('tvdbId')
            for target_episode in episodes:
                if any(f"tvdb://{episode_tvdb_id}" in g.id for g in target_episode.guids):
                    logger.info("✅ Episodio trovato con episode_tvdb_id ID %s", episode_tvdb_id)
                    # Forza l'aggiornamento dei metadati per assicurarsi che siano completi
                    target_episode.refresh()
                    target_episode.reload()
                    languages = [track.language for track in target_episode.media[0].parts[0].streams if
                                 track.streamType == 2]
        elif media.type in ("movie", "show"):
            media.reload()
            languages = [track.language for track in media.media[0].parts[0].streams if track.streamType == 2]

        languages = list(dict.fromkeys(languages))
        return media, languages, id

    def process_webhook_data(self, data):
        """Riceve i dati da Sonarr/Radarr al momento del download"""
        media, languages, id = self.get_languages(data)
        if not media:
            return

        audio_db = _load_audio_db()
        audio_db[id] = languages
        _save_audio_db(audio_db)

        logger.info("🎧 Tracce audio salvate per %s: %s", media.title, languages)
        return languages

    async def check_language_update(self, data):
        """Controlla se è stata aggiunta la lingua italiana"""
        time.sleep(10)
        media, current_languages, id = self.get_languages(data)
        if not media:
            logger.warning("⚠️ Media non trovato dopo import")
            return

        audio_db = _load_audio_db()
        previous_languages = audio_db.get(id, [])

        if media and not data.get('isUpgrade'):
            await self.send_telegram_notification(media.title, current_languages, media.summary, media.thumbUrl)
            return "Notifica aggiunto inviata"
        elif "Italian" in current_languages and "Italian" not in previous_languages:
            await self.send_telegram_notification(media.title, current_languages, media.summary, media.thumbUrl)
            return "Notifica italiano inviata"
        else:
            return "Nessun cambiamento rilevante"
