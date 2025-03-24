# Usa un'immagine Python leggera
FROM python:3.12-alpine

# Imposta la working directory all'interno del container
WORKDIR /app

# Copia i file nel container
COPY requirements.txt .
COPY plexguard/ ./plexguard/
COPY plexguard/Controller.py ./plexguard.py
RUN echo '{}' > audio_tracks.json

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# (Opzionale) Definisci variabili d’ambiente documentative
# Puoi sovrascriverle con -e in docker run o nel docker-compose.yml
#ENV QBITTORRENT_URL=""
#ENV QBITTORRENT_USER=""
#ENV QBITTORRENT_PASS=""
#ENV DAYS_OLD=90
#ENV PLEX_URL=""
#ENV PLEX_TOKEN=""
#ENV TELEGRAM_BOT_TOKEN=""
#ENV TELEGRAM_CHAT_ID=""

# Espone la porta (opzionale, utile se usi Docker con docker-compose o host binding)
EXPOSE 5001

# Comando di avvio
CMD ["python", "plexguard.py"]
