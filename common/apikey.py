from datetime import datetime

from pytz import utc

import db_control
from app_view import CVAdminModelView
from plugin import PluginsRegistry

__registry__ = cr = PluginsRegistry()

db = db_control.get_db()


class APIKey(db.Model):
    __bind_key__ = 'default'
    __tablename__ = 'apikey'

    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    botid = db.Column(db.String(20), nullable = False, unique = True)
    key = db.Column(db.String(255), nullable = False, unique = True)
    secret = db.Column(db.String(255), nullable = False)
    createtime = db.Column(db.Integer, nullable = False, default = int(datetime.now(tz = utc).timestamp()))

    @staticmethod
    def find_by_key(key):
        return APIKey.query.filter_by(key = key).first()

    @staticmethod
    def find_by_bot(bitid):
        return APIKey.query.filter_by(bitid = bitid).first()


class APIKeyView(CVAdminModelView):
    can_create = True
    can_edit = False
    can_delete = True

    column_labels = dict(id = 'ID', botid = '机器人ID', key = 'API Key', secret = 'API Secret', createtime = '创建时间')
    column_formatters = dict(createtime = lambda v, c, m, p: datetime.fromtimestamp(m.createtime).strftime('%Y-%m-%d'))
    form_columns = ('botid', 'key', 'secret')

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, 'API密钥', '系统设置')


db.create_all()


@cr.model('94-APIKey')
def get_apikey_model():
    return APIKey


@cr.view('94-APIKey')
def get_apikey_view():
    return APIKeyView