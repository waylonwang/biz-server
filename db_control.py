import os

from flask_babelex import Babel
from flask_sqlalchemy import SQLAlchemy

from env import get_default_db_path, get_db_dir, get_config as config

_db = None


def init(app):
    app.config.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite:///' + get_default_db_path())
    app.config.setdefault('SQLALCHEMY_BINDS', get_db_binds())
    app.config.setdefault('SQLALCHEMY_ECHO', True)
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
    babel = Babel(app)

    @babel.localeselector
    def get_locale():
        return 'zh_Hans_CN'

    global _db
    _db = SQLAlchemy(app)
    return _db


def set_db(db):
    global _db
    _db = db


def get_db():
    global _db
    return _db


def get_db_binds() -> dict:
    binds = config().get('db_binds', {})
    db_binds = {}
    for (k, v) in binds.items():
        db_binds[k] = 'sqlite:///' + os.path.join(get_db_dir(), v)
    return db_binds