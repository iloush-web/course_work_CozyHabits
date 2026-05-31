import os

basedir = os.path.abspath(os.path.dirname(__file__))


def _normalize_db_url(url: str) -> str:
    # SQLAlchemy ожидает префикс 'postgresql://', а не 'postgres://'
    if url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql://', 1)
    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', '1') == '1'

    SQLALCHEMY_DATABASE_URI = _normalize_db_url(os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(basedir, 'cozyhabits.db')
    ))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
