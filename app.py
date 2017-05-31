from flask import Flask

import api_control as api
import db_control as db
from env import get_env_host, get_env_port
import common.oauth as oauth

app = Flask(__name__)
db.init(app)
api.init(app)
oauth.init(app)

if __name__ == '__main__':
    import plugin
    import app_view as view
    import common.user as user

    plugin.load_plugins('common', app)
    plugin.load_plugins('plugins', app)

    user.init()
    view.init(app)

    app.run(host = get_env_host(), port = get_env_port())