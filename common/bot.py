import db_control
from datetime import datetime

from pytz import utc
from app_view import CVAdminModelView
from plugin import PluginsRegistry

__registry__ = cr = PluginsRegistry()

db = db_control.get_db()

class Bot(db.Model):
    __bind_key__ = 'default'
    __tablename__ = 'bot'

    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    createtime = db.Column(db.Integer, nullable=False, default=int(datetime.now(tz=utc).timestamp()))
    updatetime = db.Column(db.Integer, nullable=False, default=int(datetime.now(tz=utc).timestamp()))
    remark = db.Column(db.String(255), nullable=True)

class BotView(CVAdminModelView):
    can_create = True
    can_edit = True
    can_delete = True

    column_display_pk = True

    column_labels = dict(id='机器人ID', name='名称', createtime='创建时间', updatetime='更新时间', remark='备注')
    column_formatters = dict(createtime=lambda v, c, m, p: datetime.fromtimestamp(m.createtime).strftime('%Y-%m-%d'),
                             updatetime=lambda v, c, m, p: datetime.fromtimestamp(m.updatetime).strftime('%Y-%m-%d'))
    form_columns = ('id', 'name', 'remark')
    form_edit_rules = ('id', 'name', 'remark')
    form_create_rules = ('id', 'name', 'remark')

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '机器人','系统设置')


db.create_all()


@cr.model('93-Bot')
def get_bot_model():
    return Bot


@cr.view('93-Bot')
def get_bot_view():
    return BotView
