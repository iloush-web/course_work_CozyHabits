"""Точка входа для production-сервера (waitress) в контейнере."""
import os

from waitress import serve

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # threads=2 — экономим память на слабом VPS (по умолчанию waitress берёт 4).
    # channel_timeout — закрываем зависшие соединения, чтобы не копились.
    serve(
        app,
        host='0.0.0.0',
        port=port,
        threads=int(os.environ.get('WAITRESS_THREADS', 2)),
        channel_timeout=60,
    )
