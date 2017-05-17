from flask import Flask


import db_control as db
import api_control as api
from env import get_env_host, get_env_port

app = Flask(__name__)
db.init(app)
api.init(app)


if __name__ == '__main__':
    import plugin
    import app_view as view

    plugin.load_plugins('common', app)
    plugin.load_plugins('plugins', app)

    view.init(app)

    app.run(host=get_env_host(), port=get_env_port())
