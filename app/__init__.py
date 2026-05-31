import os

from flask import Flask

from config import Config
from app.extensions import db, bcrypt, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    from app.routes import main
    from app.auth import auth
    from app.admin import admin
    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(admin)

    os.makedirs(os.path.join(app.static_folder, 'uploads', 'habits'), exist_ok=True)
    os.makedirs(os.path.join(app.static_folder, 'uploads', 'rewards'), exist_ok=True)
    os.makedirs(os.path.join(app.static_folder, 'uploads', 'avatars'), exist_ok=True)

    with app.app_context():
        from app import models  # noqa: F401  register models with SQLAlchemy
        db.create_all()

    return app
