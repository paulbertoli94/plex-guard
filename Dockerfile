# Usa Python 3.12
FROM python:3.12-alpine

# Imposta la directory di lavoro
WORKDIR /app

# Copia i file necessari
COPY requirements.txt requirements.txt
COPY sonarr_webhook.py sonarr_webhook.py

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Dichiarare variabili d'ambiente (opzionale, utile per documentazione)
#ENV QBITTORRENT_URL="http://127.0.0.1:8080"
#ENV QBITTORRENT_USER="admin"
#ENV QBITTORRENT_PASS="password"
#ENV DAYS_OLD = os.getenv("DAYS_OLD", 90)

# Comando di avvio
CMD ["python", "sonarr_webhook.py"]
