from flask import Flask

from config import Config
from app.extensions import db, bcrypt


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)

    from app.routes import main
    app.register_blueprint(main)

    with app.app_context():
        from app import models  # noqa: F401  register models with SQLAlchemy
        db.create_all()

    return app
