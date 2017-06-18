from datetime import datetime, timedelta

from flask_restful import Resource, reqparse
from sqlalchemy import case, func, and_

import api_control as ac
import db_control
from app_view import CVAdminModelView
from common.util import get_now, get_botname, get_target_composevalue, get_target_display, output_datetime,\
    generate_key,\
    get_yesno_display, display_datetime, get_list_by_botassign,\
    get_list_count_by_botassign, get_CQ_display
from plugin import PluginsRegistry
from plugins.setting import BotParam

__registry__ = pr = PluginsRegistry()

# Model----------------------------------------------------------------------------------------------------
db = db_control.get_db()


@pr.register_model(20)
class Point(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'point_record'

    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    botid = db.Column(db.String(20), nullable = False)
    target = db.Column(db.String(20), nullable = False)
    member_id = db.Column(db.String(20), nullable = False)
    member_name = db.Column(db.String(20), nullable = False)
    reporter_id = db.Column(db.String(20), nullable = False)
    reporter_name = db.Column(db.String(20), nullable = False)
    point = db.Column(db.Integer, nullable = False, default = 1)
    confirm_code = db.Column(db.String(4), nullable = False, default = lambda: generate_key(4, False, False, True))
    has_confirmed = db.Column(db.Integer, nullable = True, default = 0)
    is_newbie = db.Column(db.Integer, nullable = True, default = 0)
    date = db.Column(db.Date, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now(),
                     index = True)
    time = db.Column(db.Time, nullable = False, default = lambda: datetime.time(get_now()),
                     onupdate = lambda: datetime.time(get_now()),
                     index = True)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    update_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now())
    message = db.Column(db.String(20), nullable = False)

    @staticmethod
    def create(botid, target_type, target_account, member_id, reporter_id, point: int, message, is_newbie: bool = False,
               **kwargs):
        target = get_target_composevalue(target_type, target_account)

        Point.check_limit(botid, target, member_id, reporter_id, point, get_now().strftime('%Y-%m-%d'), is_newbie)

        record = Point(botid = botid,
                       target = target,
                       member_id = member_id,
                       member_name = '' if kwargs.get('member_name') is None else kwargs.get('member_name'),
                       reporter_id = reporter_id,
                       reporter_name = '' if kwargs.get('reporter_name') is None else kwargs.get('reporter_name'),
                       point = point,
                       is_newbie = 1 if is_newbie else 0,
                       message = message)
        record.query.session.add(record)
        record.query.session.commit()
        return PointConfirm.create(botid, target_type, target_account, record.id, record.member_id, record.confirm_code)

    @staticmethod
    def check_limit(botid, target, member_id, reporter_id, point: int, date, is_newbie: bool = False):
        member_limit = int(BotParam.find(botid, 'point_accept_limit').value)
        if is_newbie:
            report_limit = int(BotParam.find(botid, 'point_newbie_limit').value)
        else:
            report_limit = int(BotParam.find(botid, 'point_normal_limit').value)
        result = Point.get_report_count(botid, target, member_id, reporter_id, date)
        if int(result.reporter_confirmed_total) + point > report_limit:
            raise Exception('报点数超过了报点人今天累计的上限')
        elif int(result.member_confirmed_total) + point > member_limit:
            raise Exception('报点数超过了受报人接受累计的上限')

    @staticmethod
    def get_report_count(botid, target, member_id, reporter_id, date):
        return Point.query.session.query(
            func.ifnull(
                func.sum(
                    case(
                        [(Point.has_confirmed == 1, Point.point)],
                        else_ = 0
                    )
                ), 0
            ).label('reporter_confirmed_total'),
            func.ifnull(
                func.sum(
                    case(
                        [(
                            and_(Point.has_confirmed == 1, Point.member_id == member_id),
                            Point.point
                        )],
                        else_ = 0
                    )
                ), 0
            ).label("member_confirmed_total"),
            func.ifnull(
                func.sum(
                    case(
                        [(Point.has_confirmed == 0, Point.point)],
                        else_ = 0
                    )
                ), 0
            ).label('reporter_unconfirm_total'),
            func.ifnull(
                func.sum(
                    case(
                        [(
                            and_(Point.has_confirmed == 0, Point.member_id == member_id),
                            Point.point
                        )],
                        else_ = 0
                    )
                ), 0
            ).label("member_unconfirm_total")
        ).filter(
            Point.botid == botid,
            Point.target == target,
            Point.reporter_id == reporter_id,
            Point.date == date
        ).first()

    @staticmethod
    def get_report_status(botid, target_type, target_account, reporter_id, ):
        target = get_target_composevalue(target_type, target_account)
        result = Point.get_report_count(botid, target, '0', reporter_id, output_datetime(get_now(), True, False))
        status = {}
        status['botid'] = botid
        status['target'] = target
        status['reporter_id'] = reporter_id
        status['reporter_confirmed_total'] = result.reporter_confirmed_total
        status['reporter_unconfirm_total'] = result.reporter_unconfirm_total
        return status

    @staticmethod
    def confirm(id, is_newbie: bool = False):
        point = Point.query.get(id)

        Point.check_limit(point.botid, point.target, point.member_id, point.reporter_id, point.point, point.date,
                          is_newbie)

        point.has_confirmed = 1
        Point.query.session.commit()

        return point

    @staticmethod
    def find_first_by_member_name(member_name):
        return Point.query.filter_by(member_name = member_name).first()

    @staticmethod
    def get_total(botid, target_type, target_account, date_from, date_to, member = None):
        target = get_target_composevalue(target_type, target_account)

        if member is None:
            member_id = None
        elif not member.isdigit():
            record = Point.find_first_by_member_name(member)
            member_id = record.member_id
        else:
            member_id = member

        return Point.query.session.query(
            func.sum(Point.point).label('total_full'),
            func.sum(case([(Point.has_confirmed == 1 , Point.point)], else_ = 0)).label('total_success'),
        ).filter(
            Point.botid == botid,
            Point.target == target,
            Point.date >= date_from,
            Point.date <= date_to,
            Point.member_id == member_id if member_id is not None else 1 == 1
        ).first()

@pr.register_model(21)
class PointConfirm(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'point_confirm'

    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    botid = db.Column(db.String(20), nullable = False)
    target = db.Column(db.String(20), nullable = False)
    point_id = db.Column(db.Integer, nullable = False)
    member_id = db.Column(db.String(20), nullable = False)
    confirm_code = db.Column(db.String(4), nullable = False, default = lambda: generate_key(4, False, False, True))
    expire_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now() + timedelta(minutes = 30))

    @staticmethod
    def create(botid, target_type, target_account, point_id, member_id, confirm_code):
        PointConfirm.clear(botid, target_type, target_account)
        target = get_target_composevalue(target_type, target_account)
        record = PointConfirm(botid = botid,
                              target = target,
                              point_id = point_id,
                              member_id = member_id,
                              confirm_code = confirm_code)
        PointConfirm.query.session.add(record)
        PointConfirm.query.session.commit()
        return record

    @staticmethod
    def clear(botid, target_type, target_account):
        target = get_target_composevalue(target_type, target_account)
        PointConfirm.query.filter(PointConfirm.botid == botid,
                                  PointConfirm.target == target,
                                  PointConfirm.expire_at <= get_now()).delete()
        PointConfirm.query.session.commit()

    @staticmethod
    def confirm(botid, target_type, target_account, member_id, confirm_code, is_newbie: bool = False):
        PointConfirm.clear(botid, target_type, target_account)
        target = get_target_composevalue(target_type, target_account)
        records = PointConfirm.query.filter(PointConfirm.botid == botid,
                                            PointConfirm.target == target,
                                            PointConfirm.member_id == member_id,
                                            PointConfirm.confirm_code == confirm_code).all()
        if len(records) > 0:
            # for record in records:
            record = records[0]
            point = Point.confirm(record.point_id, is_newbie)
            PointConfirm.query.session.delete(record)
            PointConfirm.query.session.commit()
            return point
        else:
            raise Exception('确认码[' + confirm_code + ']无效，请检查是否已经过期')


# View-----------------------------------------------------------------------------------------------------
@pr.register_view()
class PointView(CVAdminModelView):
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 100
    column_filters = ('target', 'member_id', 'member_name', 'reporter_id', 'reporter_name', 'has_confirmed', 'date')
    column_list = (
        'botid', 'target', 'member', 'reporter', 'point', 'confirm_code', 'has_confirmed',
        'date', 'time', 'update_at', 'message')
    column_searchable_list = ('member_name', 'reporter_name')
    column_labels = dict(botid = '机器人', target = '目标',
                         member = '成员', reporter = '报点人',
                         point = '点数', confirm_code = '确认码', has_confirmed = '已经确认',
                         date = '日期', time = '时间', create_at = '创建时间', update_at = '更新时间',
                         message = '消息')
    column_formatters = dict(botid = lambda v, c, m, p: get_botname(m.botid),
                             target = lambda v, c, m, p: get_target_display(m.target),
                             member = lambda v, c, m, p: get_CQ_display(m.member_id + ' : ' + m.member_name),
                             reporter = lambda v, c, m, p: get_CQ_display(m.reporter_id + ' : ' + m.reporter_name),
                             has_confirmed = lambda v, c, m, p: get_yesno_display(m.has_confirmed),
                             date = lambda v, c, m, p: display_datetime(m.create_at, False),
                             time = lambda v, c, m, p: m.time.strftime('%H:%M'),
                             update_at = lambda v, c, m, p: display_datetime(m.update_at),
                             message = lambda v, c, m, p: get_CQ_display(m.message))

    column_default_sort = ('id', True)

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '报点记录', '报点管理')

    def get_query(self):
        return get_list_by_botassign(Point, PointView, self)

    def get_count_query(self):
        return get_list_count_by_botassign(Point, PointView, self)


# todo point的内容显示为记录详情
@pr.register_view()
class PointConfirmView(CVAdminModelView):
    can_create = False
    can_edit = False
    can_delete = True
    page_size = 100
    column_filters = ('target', 'expire_at')
    column_list = (
        'botid', 'target', 'point', 'confirm_code', 'expire_at')
    column_searchable_list = ('confirm_code',)
    column_labels = dict(botid = '机器人', target = '目标',
                         point = '报点记录', confirm_code = '确认码', expire_at = '过期时间')
    column_formatters = dict(botid = lambda v, c, m, p: get_botname(m.botid),
                             target = lambda v, c, m, p: get_target_display(m.target),
                             point = lambda v, c, m, p: m.point_id,
                             expire_at = lambda v, c, m, p: display_datetime(m.expire_at))

    column_default_sort = ('id', True)

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '待确认队列', '报点管理')

    def get_query(self):
        return get_list_by_botassign(PointConfirm, PointConfirmView, self)

    def get_count_query(self):
        return get_list_count_by_botassign(PointConfirm, PointConfirmView, self)


# Control--------------------------------------------------------------------------------------------------
@ac.register_api('/pointreport', endpoint = 'pointreport')
class PointAPI(Resource):
    method_decorators = [ac.require_apikey]

    def post(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('target_type', required = True, help = '请求中必须包含target_type')
            parser.add_argument('target_account', required = True, help = '请求中必须包含target_account')
            parser.add_argument('member_id', required = True, help = '请求中必须包含member_id')
            parser.add_argument('member_name')
            parser.add_argument('reporter_id', required = True, help = '请求中必须包含reporter_id')
            parser.add_argument('reporter_name')
            parser.add_argument('point', type = int, required = True, choices = (1, 2), help = '请求中必须包含point,且只能为1或2')
            parser.add_argument('message', required = True, help = '请求中必须包含message')
            parser.add_argument('is_newbie', type = bool)
            args = parser.parse_args()
            kwargs = {}
            kwargs['member_name'] = args['member_name']
            kwargs['reporter_name'] = args['reporter_name']
            if args['is_newbie'] is not None: kwargs['is_newbie'] = args['is_newbie']
            record = Point.create(ac.get_bot(),
                                  args['target_type'],
                                  args['target_account'],
                                  args['member_id'],
                                  args['reporter_id'],
                                  args['point'],
                                  args['message'],
                                  **kwargs)
            if record is not None:
                return ac.success(botid = record.botid,
                                  target = record.target,
                                  reporter_id = args['reporter_id'],
                                  reporter_name = args['reporter_name'],
                                  member_id = args['member_id'],
                                  member_name = args['member_name'],
                                  point = args['point'],
                                  confirm_code = record.confirm_code,
                                  expire_at = output_datetime(record.expire_at))
            else:
                return ac.fault(error = Exception('未知原因导致数据创建失败'))
        except Exception as e:
            return ac.fault(error = e)


@ac.register_api('/pointconfirm', endpoint = 'pointconfirm')
class PointConfirmAPI(Resource):
    method_decorators = [ac.require_apikey]

    def patch(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('target_type', required = True, help = '请求中必须包含target_type')
            parser.add_argument('target_account', required = True, help = '请求中必须包含target_account')
            parser.add_argument('member_id', required = True, help = '请求中必须包含member_id')
            parser.add_argument('confirm_code', required = True, help = '请求中必须包含confirm_code')
            parser.add_argument('is_newbie', type = bool)
            args = parser.parse_args()
            kwargs = {}
            if args['is_newbie'] is not None: kwargs['is_newbie'] = args['is_newbie']
            record = PointConfirm.confirm(ac.get_bot(),
                                          args['target_type'],
                                          args['target_account'],
                                          args['member_id'],
                                          args['confirm_code'],
                                          **kwargs)
            if record is not None:
                return ac.success(botid = record.botid,
                                  target = record.target,
                                  reporter_id = record.reporter_id,
                                  reporter_name = record.reporter_name,
                                  member_id = record.member_id,
                                  member_name = record.member_name,
                                  point = record.point,
                                  has_confirmed = record.has_confirmed)
            else:
                return ac.fault(error = Exception('未知原因导致数据创建失败'))
        except Exception as e:
            return ac.fault(error = e)


@ac.register_api('/pointreportstatus', endpoint = 'pointreportstatus')
class PointReportStatusAPI(Resource):
    method_decorators = [ac.require_apikey]

    def get(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('target_type', required = True, help = '请求中必须包含target_type')
            parser.add_argument('target_account', required = True, help = '请求中必须包含target_account')
            parser.add_argument('reporter_id', required = True, help = '请求中必须包含reporter_id')
            args = parser.parse_args()

            record = Point.get_report_status(ac.get_bot(),
                                             args['target_type'],
                                             args['target_account'],
                                             args['reporter_id'])
            if record is not None:
                return ac.success(status = record)
            else:
                return ac.fault(error = Exception('未知原因导致数据创建失败'))
        except Exception as e:
            return ac.fault(error = e)