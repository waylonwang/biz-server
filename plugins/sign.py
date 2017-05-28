from datetime import datetime

from flask_restful import Resource

import api_control as ac
import db_control
from app_view import CVAdminModelView
from common.util import get_now, get_botname, get_target_value, get_omit_display,\
    get_target_display
from plugin import PluginsRegistry

__registry__ = pr = PluginsRegistry()

# Model----------------------------------------------------------------------------------------------------
db = db_control.get_db()


@pr.register_model(11)
class Sign(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'sign'

    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    botid = db.Column(db.String(20), nullable = False)
    target = db.Column(db.String(20), nullable = False)
    member_id = db.Column(db.String(20), nullable = False)
    member_name = db.Column(db.String(20), nullable = False)
    date = db.Column(db.Date, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now().date,
                     index = True)
    time = db.Column(db.Time, nullable = False, default = lambda: datetime.time(get_now()),
                     onupdate = lambda: datetime.time(get_now()),
                     index = True)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    message = db.Column(db.String(20), nullable = False)

    @staticmethod
    def create(botid, target_type, target_account, member_id, message, **kwargs):
        target = get_target_value(target_type, target_account)
        record = Sign(botid = botid,
                      target = target,
                      member_id = member_id,
                      member_name = '' if kwargs.get('member_name') == None else kwargs.get('member_name'),
                      # date = datetime.now(tz = timezone('Asia/Shanghai')).strftime('%Y-%m-%d') if kwargs.get(
                      #     'date') is None else kwargs.get('date'),
                      # time = datetime.now(tz = timezone('Asia/Shanghai')).strftime('%H:%M') if kwargs.get(
                      #     'time') is None else kwargs.get('time'),
                      # timemark = int(datetime.now(tz = utc).timestamp()) if kwargs.get(
                      #     'timemark') is None else kwargs.get('timemark'),
                      message = message)
        record.query.session.add(record)
        record.query.session.commit()
        return record


# View-----------------------------------------------------------------------------------------------------
@pr.register_view()
class SignView(CVAdminModelView):
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 100
    column_filters = ('target', 'member_id', 'member_name', 'date')
    column_list = (
        'botid', 'target', 'member_id', 'member_name', 'date', 'time', 'message')
    column_searchable_list = ('member_name',)
    column_labels = dict(botid = '机器人', target = '目标',
                         member_id = '成员账号', member_name = '成员名称',
                         date = '日期', time = '时间',
                         message = '消息')
    column_formatters = dict(botid = lambda v, c, m, p: get_botname(m.botid),
                             target = lambda v, c, m, p: get_target_display(m.target),
                             member_name = lambda v, c, m, p: get_omit_display(m.member_name),
                             message = lambda v, c, m, p: get_omit_display(m.message))

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '签到记录', '消息管理')


# Control--------------------------------------------------------------------------------------------------
@ac.register_api('/sign', endpoint = 'sign')
class SignAPI(Resource):
    method_decorators = [ac.require_apikey]

    def post(self):
        pass