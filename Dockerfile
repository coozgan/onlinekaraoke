FROM python:3.13-slim
# yt-dlp does the YouTube search, qrencode draws the join QR code.
RUN apt-get update && apt-get install -y --no-install-recommends qrencode \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir -U yt-dlp \
 && useradd -r -u 10001 karaoke
WORKDIR /app
COPY server.py tv.html remote.html ./
USER karaoke
EXPOSE 8010
CMD ["python3", "-u", "server.py"]
