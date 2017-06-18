from datetime import datetime

from flask_restful import Resource, reqparse
from sqlalchemy import func

import api_control as ac
import db_control
from app_view import CVAdminModelView
from common.util import get_now, get_botname, get_target_composevalue, get_target_display, output_datetime,\
    display_datetime,\
    get_list_by_botassign, get_list_count_by_botassign, get_CQ_display
from plugin import PluginsRegistry
from plugins.score import ScoreRecord
from plugins.setting import BotParam

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
        sign = Sign.find_by_date(botid, target_type, target_account, member_id, get_now().strftime('%Y-%m-%d'),
                                 get_now().strftime('%Y-%m-%d'), )
        if len(sign) > 0:
            raise Exception(
                member_id + ':' + ('' if kwargs.get('member_name') is None else kwargs.get('member_name')) + '今天已经签过到了')

        target = get_target_composevalue(target_type, target_account)
        record = Sign(botid = botid,
                      target = target,
                      member_id = member_id,
                      member_name = '' if kwargs.get('member_name') is None else kwargs.get('member_name'),
                      # date = datetime.now(tz = timezone('Asia/Shanghai')).strftime('%Y-%m-%d') if kwargs.get(
                      #     'date') is None else kwargs.get('date'),
                      # time = datetime.now(tz = timezone('Asia/Shanghai')).strftime('%H:%M') if kwargs.get(
                      #     'time') is None else kwargs.get('time'),
                      # timemark = int(datetime.now(tz = utc).timestamp()) if kwargs.get(
                      #     'timemark') is None else kwargs.get('timemark'),
                      message = message)
        record.query.session.add(record)
        record.query.session.commit()
        sign_code = BotParam.find(botid, 'sign_code')
        if sign_code is not None:
            ScoreRecord.create_change(sign_code.value, member_id,
                                      member_name = kwargs.get('member_name'), botid = botid)

        return record

    @staticmethod
    def find_by_date(botid, target_type, target_account, member_id, date_from, date_to):
        target = get_target_composevalue(target_type, target_account)
        return Sign.query.filter(Sign.botid == botid,
                                 Sign.target == target,
                                 Sign.member_id == member_id,
                                 Sign.date >= date_from,
                                 Sign.date <= date_to).all()

    @staticmethod
    def find_first_by_member_name(member_name):
        return Sign.query.filter_by(member_name = member_name).first()

    @staticmethod
    def get_count(botid, target_type, target_account, date_from, date_to, member = None):
        target = get_target_composevalue(target_type, target_account)

        if member is None:
            member_id = None
        elif not member.isdigit():
            record = Sign.find_first_by_member_name(member)
            member_id = record.member_id
        else:
            member_id = member

        return Sign.query.session.query(
            func.sum(1).label('cnt')
        ).filter(
            Sign.botid == botid,
            Sign.target == target,
            Sign.date >= date_from,
            Sign.date <= date_to,
            Sign.member_id == member_id if member_id is not None else 1 == 1
        ).first()

# View-----------------------------------------------------------------------------------------------------
@pr.register_view()
class SignView(CVAdminModelView):
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 100
    column_filters = ('target', 'member_id', 'member_name', 'date')
    column_list = (
        'botid', 'target', 'member', 'date', 'time', 'message')
    column_searchable_list = ('member_name',)
    column_labels = dict(botid = '机器人', target = '目标',
                         member = '成员', member_id = '成员账号', member_name = '成员名称',
                         date = '日期', time = '时间',
                         message = '消息')
    column_formatters = dict(botid = lambda v, c, m, p: get_botname(m.botid),
                             target = lambda v, c, m, p: get_target_display(m.target),
                             member = lambda v, c, m, p: get_CQ_display(m.member_id + ' : ' + m.member_name),
                             message = lambda v, c, m, p: get_CQ_display(m.message),
                             date = lambda v, c, m, p: display_datetime(m.create_at, False),
                             time = lambda v, c, m, p: m.time.strftime('%H:%M'))

    column_default_sort = ('id', True)

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '签到记录', '消息管理')

    def get_query(self):
        return get_list_by_botassign(Sign, SignView, self)

    def get_count_query(self):
        return get_list_count_by_botassign(Sign, SignView, self)


# Control--------------------------------------------------------------------------------------------------
@ac.register_api('/sign', endpoint = 'sign')
class SignAPI(Resource):
    method_decorators = [ac.require_apikey]

    def post(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('target_type', required = True, help = '请求中必须包含target_type')
            parser.add_argument('target_account', required = True, help = '请求中必须包含target_account')
            parser.add_argument('member_id', required = True, help = '请求中必须包含member_id')
            parser.add_argument('member_name')
            parser.add_argument('message', required = True, help = '请求中必须包含message')
            args = parser.parse_args()
            record = Sign.create(ac.get_bot(),
                                 args['target_type'],
                                 args['target_account'],
                                 args['member_id'],
                                 args['message'],
                                 member_name = args['member_name'])
            if record is not None:
                return ac.success(botid = record.botid,
                                  target = record.target,
                                  member_id = record.member_id,
                                  member_name = record.member_name,
                                  date = output_datetime(record.date),
                                  time = output_datetime(record.time),
                                  create_at = output_datetime(record.create_at),
                                  message = record.message)
            else:
                return ac.fault(error = Exception('未知原因导致数据创建失败'))
        except Exception as e:
            return ac.fault(error = e)