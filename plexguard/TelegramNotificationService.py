import asyncio
import io
import json
import logging
import os
import re
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
    imdb_id = data.get("series", {}).get("tmdbId")
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


def save_languages_on_db(title, media, languages, id):
    if not media or not languages:
        return

    audio_db = _load_audio_db()
    audio_db[id] = languages
    _save_audio_db(audio_db)

    logger.info("🎧 Tracce audio salvate per %s: %s", title, languages)
    return title, languages


def start_kometa(libraries):
    # Define the URL of the endpoint
    url = "http://192.168.1.10:5009/kometa"

    # Define the payload with the "libraries" parameter
    payload = {
        "libraries": libraries
    }

    # Make a POST request to the endpoint with a JSON payload
    response = requests.post(url, json=payload)

    # Check the status code and print the result
    if response.status_code == 200:
        print("Response kometa:", response.json())
    else:
        print("Request kometa failed with status code:", response.status_code)
        print("Error kometa response:", response)


class TelegramNotificationService:
    def __init__(self):
        """ Inizializza il servizio di notifica con connessione a Plex e Telegram """
        self.plex_url = os.getenv("PLEX_URL")
        self.plex_token = os.getenv("PLEX_TOKEN")
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.tmdb_api_key = os.getenv("TMDB_API_KEY")
        self.plex = None
        self.bot = None

        # Verifica i parametri e inizializza i servizi
        self._initialize_telegram()

    def _initialize_plex(self):
        """ Inizializza la connessione a Plex, se possibile """
        if not self.plex_url or not self.plex_token:
            logger.warning("⚠️ Parametri Plex mancanti: il servizio Plex non sarà attivo.")
            return

        try:
            self.plex = PlexServer(self.plex_url, self.plex_token)
            logger.info("✅ Connessione a Plex avvenuta con successo!")
            self.plex.library.update()
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

    def normalize_data(self, data):
        if data.get('type') and (data.get('type') == 'season' or data.get('type') == 'episode'):
            data['episodes'] = []
            episode_numbers = [int(x) for x in data.get('series').get('episodeNumber').split("-") if x]
            for episodeNumber in episode_numbers:
                episode_info = {
                    "episodeNumber": episodeNumber,
                    "seasonNumber": data.get('series', {}).get('seasonNumber')
                }
                data['episodes'].append(episode_info)
        self._initialize_plex()

    def _find_media_by_id(self, data):
        if data.get('movie'):
            tmdb_id = data.get('movie').get('tmdbId')
            logger.info("🔍 Ricerca Plex per tmdbId: %s", tmdb_id)
            for section in self.plex.library.sections():
                if section.type == 'movie':
                    results = section.search(title="")
                    for item in results:
                        if any(f"tmdb://{tmdb_id}" == g.id for g in item.guids):
                            logger.info("✅ Trovato '%s' con tmdbId %s nella sezione '%s'",
                                        item.title, tmdb_id, section.title)
                            item.refresh()
                            item.reload()
                            return item.title, item, tmdb_id, 'movie'

        if data.get('series'):
            tmdb_id = data.get('series').get('tmdbId')
            logger.info("🔍 Ricerca Plex per tmdbId: %s", tmdb_id)
            for section in self.plex.library.sections():
                if section.type == 'show':
                    results = section.search(title="")
                    for item in results:
                        if any(f"tmdb://{tmdb_id}" == g.id for g in item.guids):
                            logger.info("🔍 Ricerca episodio '%s' con tmdbId %s nella sezione '%s'",
                                        item.title, tmdb_id, section.title)
                            item.refresh()
                            item.reload()
                            if item.episodes():
                                payload_episode_id = f"{tmdb_id}-s{int(data.get('seasonNumber')):02d}e{int(data.get('episodeNumber')):02d}"
                                episodes = item.episodes()
                                for target_episode in episodes:
                                    target_id = f"{tmdb_id}-{target_episode.seasonEpisode}"
                                    if target_id == payload_episode_id:
                                        logger.info("✅ Episodio trovato con episode_tmdbId ID %s", target_id)
                                        # Forza l'aggiornamento dei metadati per assicurarsi che siano completi
                                        target_episode.refresh()
                                        target_episode.reload()
                                        return f"{item.title} - {target_episode.title} - {str.upper(target_episode.seasonEpisode)}", target_episode, target_id, 'series'

        return None, None, None, None

    async def send_telegram_notification(self, title, current_languages, summary, media_id, media_type):
        """Invia una notifica su Telegram con messaggio e immagine.

        L'URL dell'immagine viene scaricato e inviato come file.
        Questa funzione è interamente asincrona e deve essere chiamata con `await`.
        """
        if not self.bot:
            logger.warning("⚠️ Nessuna connessione Telegram disponibile. Notifica non inviata.")
            return False

        try:
            if media_type == "movie":
                image_url = self.get_tmdb_italian_movie_poster(media_id)
            else:
                image_url = self.get_tmdb_episode_still(media_id)

            # Scarica l'immagine dall'URL in modo sincrono
            # (Se vuoi farlo asincrono puoi usare aiohttp, ma qui restiamo semplici)
            response = requests.get(image_url)
            if response.status_code != 200:
                logger.error("❌ Errore nel download dell'immagine: %s", response.status_code)
                return False

            # Converte il contenuto in un file-like object
            image_bytes = io.BytesIO(response.content)

            # Sostituisci ogni lingua con la sua emoji (se disponibile)
            flags = [flag_mapping.get(lang, lang) for lang in current_languages]

            message = (
                f"<b>{title}</b>\n"
                f"<b>Tracce audio: {' '.join(flags)}</b>\n"
                f"{summary}"
            )
            if media_type == 'movie':
                message += f'\n\n<a href="https://www.youtube.com/results?search_query={title} trailer">Trailer</a>'

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
        title, media, media_id, media_type = self._find_media_by_id(data)
        if not media:
            return None, None, None, None, None

        languages = [track.language for track in media.media[0].parts[0].streams if track.streamType == 2]
        languages = list(dict.fromkeys(languages))
        return title, media, languages, str(media_id), media_type

    def save_languages(self, data):
        title, media, languages, media_id, media_type = self.get_languages(data)
        return save_languages_on_db(title, media, languages, media_id)

    def process_downloading(self, data):
        """Riceve i dati da Sonarr/Radarr al momento del download"""
        self.normalize_data(data)
        save_languages_result = []

        if data.get('episodes'):
            episodes = data['episodes']
            for episode in episodes:
                data['episodeNumber'] = episode.get('episodeNumber')
                data['seasonNumber'] = episode.get('seasonNumber')

                save_languages_result.append(self.save_languages(data))
        else:
            save_languages_result.append(self.save_languages(data))

        return save_languages_result

    async def process_imported(self, data):
        """Controlla se è stata aggiunta la lingua italiana"""
        self.normalize_data(data)
        if not data.get("type"):
            logger.info("Sleep 70s")
            await asyncio.sleep(70)

        send_telegram_result_list = []
        if data.get('episodes'):
            episodes = data['episodes']
            for episode in episodes:
                data['episodeNumber'] = episode.get('episodeNumber')
                data['seasonNumber'] = episode.get('seasonNumber')

                send_telegram_result_list.append(await self.send_telegram(data))
                await asyncio.sleep(1)
        else:
            send_telegram_result_list.append(await self.send_telegram(data))

        for send_telegram_result in send_telegram_result_list:
            if "Notifica" in send_telegram_result:
                # call kometa
                libraries = 'Serie TV' if data.get('series') else ('Film' if data.get('movie') else None)
                if libraries:
                    start_kometa(libraries)
                break

        return send_telegram_result_list

    async def send_telegram(self, data):
        title, media, current_languages, media_id, media_type = self.get_languages(data)
        if not media:
            logger.warning("⚠️ Media non trovato dopo import con id: %s", media_id)
            return
        if not current_languages:
            logger.warning("⚠️ Current Languages non trovato dopo import con id: %s", media_id)
            return

        audio_db = _load_audio_db()
        previous_languages = audio_db.get(media_id, [])

        if not previous_languages:
            await self.send_telegram_notification(title, current_languages, media.summary, media_id, media_type)
            save_languages_on_db(title, media, current_languages, media_id)
            logger.info("Notifica aggiunto inviata")
            return "Notifica aggiunto inviata"
        elif "Italian" in current_languages and "Italian" not in previous_languages:
            await self.send_telegram_notification(title, current_languages, media.summary, media_id, media_type)
            save_languages_on_db(title, media, current_languages, media_id)
            logger.info("Notifica italiano inviata")
            return "Notifica italiano inviata"
        else:
            logger.info("Nessun cambiamento rilevante")
            return "Nessun cambiamento rilevante"

    def get_tmdb_italian_movie_poster(self, tmdb_id):
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/images?api_key={self.tmdb_api_key}&include_image_language=it,null"
        r = requests.get(url)
        if r.status_code != 200:
            return None
        posters = r.json().get("posters", [])
        best_image = max(posters, key=lambda s: s.get("width", 0) * s.get("height", 0))
        if not posters:
            return None
        return f"https://image.tmdb.org/t/p/original{best_image['file_path']}"

    def get_tmdb_episode_still(self, episode_str):
        tv_id, season, episode = parse_episode_string(episode_str)
        url = (
            f"https://api.themoviedb.org/3/tv/{tv_id}/season/{season}/episode/{episode}/images"
            f"?api_key={self.tmdb_api_key}&include_image_language=it,null"
        )
        r = requests.get(url)
        if r.status_code != 200:
            return None
        stills = r.json().get("stills", [])
        best_image = max(stills, key=lambda s: s.get("width", 0) * s.get("height", 0))
        if not stills:
            return None
        return f"https://image.tmdb.org/t/p/original{best_image['file_path']}"


def parse_episode_string(episode_str):
    match = re.match(r"(\d+)-s(\d{2})e(\d{2})", episode_str, re.IGNORECASE)
    if not match:
        return None, None, None
    tv_id, season, episode = match.groups()
    return tv_id, int(season), int(episode)
