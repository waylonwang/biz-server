import re
from datetime import datetime


from flask_admin.form import rules
from flask_restful import reqparse, Resource
from sqlalchemy import func, desc, case, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from wtforms import validators, fields

import api_control as ac
import db_control
from app_view import CVAdminModelView
from common.util import get_now, display_datetime, get_botname, get_target_value, get_omit_display, get_target_display
from plugin import PluginsRegistry

__registry__ = pr = PluginsRegistry()

# Model----------------------------------------------------------------------------------------------------
db = db_control.get_db()


@pr.register_model(10)
class Speak(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'speak'

    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    botid = db.Column(db.String(20), nullable = False)
    target = db.Column(db.String(20), nullable = False)
    sender_id = db.Column(db.String(20), nullable = False)
    sender_name = db.Column(db.String(20), nullable = False)
    # date = db.Column(db.String(20), nullable = False)
    # time = db.Column(db.String(20), nullable = False)
    # create_at = db.Column(db.Integer, nullable = False, default = int(datetime.now(tz = utc).timestamp()))
    date = db.Column(db.Date, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now().date,
                     index = True)
    time = db.Column(db.Time, nullable = False, default = lambda: datetime.time(get_now()),
                     onupdate = lambda: datetime.time(get_now()),
                     index = True)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    message = db.Column(db.String(20), nullable = False)
    washed_text = db.Column(db.String(20), nullable = False)
    washed_chars = db.Column(db.Integer, nullable = False)

    @staticmethod
    def create(botid, target_type, target_account, sender_id, message, **kwargs):
        target = get_target_value(target_type, target_account)
        washed_text = SpeakWash.do(botid, message)
        record = Speak(botid = botid,
                       target = target,
                       sender_id = sender_id,
                       sender_name = '' if kwargs.get('sender_name') is None else kwargs.get('sender_name'),
                       # date = datetime.now(tz = timezone('Asia/Shanghai')).strftime('%Y-%m-%d') if kwargs.get(
                       #     'date') is None else kwargs.get('date'),
                       # time = datetime.now(tz = timezone('Asia/Shanghai')).strftime('%H:%M') if kwargs.get(
                       #     'time') is None else kwargs.get('time'),
                       # create_at = int(datetime.now(tz = utc).timestamp()) if kwargs.get(
                       #     'create_at') is None else kwargs.get('create_at'),
                       message = message,
                       washed_text = washed_text,
                       washed_chars = len(washed_text))
        record.query.session.add(record)
        record.query.session.commit()
        return record

    @staticmethod
    def dowash(id):
        record = Speak.find_by_id(id)
        if record is not None:
            record.washed_text = SpeakWash.do(record.botid, record.message)
            record.washed_chars = len(record.washed_text)
            record.query.session.commit()
        return record

    @staticmethod
    def updatewash(botid, target_type, target_account, date_from, date_to):
        records = Speak.find_by_date(botid, target_type, target_account, date_from, date_to)
        count = len(records)
        for record in records:
            record.washed_text = SpeakWash.do(record.botid, record.message)
            record.washed_chars = len(record.washed_text)
        Speak.query.session.commit()
        return count

    @staticmethod
    def find_by_date(botid, target_type, target_account, date_from, date_to):
        target = get_target_value(target_type, target_account)
        return Speak.query.filter(Speak.botid == botid,
                                  Speak.target == target,
                                  Speak.date >= date_from,
                                  Speak.date <= date_to).all()

    @staticmethod
    def find_by_id(id):
        return Speak.query.filter_by(id = id).first()

    @staticmethod
    def find_first_by_sender_name(sender_name):
        return Speak.query.filter_by(sender_name = sender_name).first()

    @staticmethod
    def find_last_by_sender_name(sender_name):
        return Speak.query.filter_by(sender_name = sender_name).last()

    @staticmethod
    def get_top(botid, target_type, target_account, date_from, date_to, limit = 10, is_valid = False):
        target = get_target_value(target_type, target_account)
        baseline = 0
        if is_valid:
            from plugins.setting import BotParam
            param = BotParam.find(botid, 'baseline')
            if param is not None:
                baseline = param.value

        return Speak.query.session.query(
            Speak.sender_id, func.last(Speak.sender_name), func.count(1).label('cnt')
        ).filter(
            Speak.botid == botid,
            Speak.target == target,
            Speak.date >= date_from,
            Speak.date <= date_to,
            Speak.washed_chars >= baseline
        ).group_by(
            Speak.sender_id,
        ).order_by(
            desc('cnt')
        ).limit(limit)

    @staticmethod
    def get_count(botid, target_type, target_account, date_from, date_to, sender = None):
        target = get_target_value(target_type, target_account)
        baseline = 0
        from plugins.setting import BotParam
        param = BotParam.find(botid, 'baseline')
        if param is not None:
            baseline = int(param.value)

        if sender is None:
            sender_id = None
        elif not sender.isdigit():
            record = Speak.find_first_by_sender_name(sender)
            sender_id = record.sender_id
        else:
            sender_id = sender

        return Speak.query.session.query(
            func.sum(1).label('cnt_full'),
            func.sum(case([(Speak.washed_chars >= baseline, 1)], else_ = 0)).label("cnt_valid")
        ).filter(
            Speak.botid == botid,
            Speak.target == target,
            Speak.date >= date_from,
            Speak.date <= date_to,
            Speak.sender_id == sender_id if sender_id is not None else 1 == 1
        ).first()


@pr.register_model(73)
class SpeakWash(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'speak_wash'

    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    botid = db.Column(db.String(20), nullable = False)
    rule = db.Column(db.String(200), nullable = False)
    replace = db.Column(db.String(200), nullable = False)
    status = db.Column(db.Integer, nullable = False)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    update_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now())
    remark = db.Column(db.String(255), nullable = True)

    @staticmethod
    def create(botid, rule, replace, remark):
        wash = SpeakWash.find(botid, rule)
        if wash is None:
            wash = SpeakWash(botid = botid,
                             rule = rule,
                             replace = replace,
                             status = 1,
                             remark = remark)
            wash.query.session.add(wash)
            wash.query.session.commit()
        else:
            wash = SpeakWash.update(botid, rule, replace = replace, remark = remark)
        return wash

    @staticmethod
    def update(botid, rule, **kwargs):
        wash = SpeakWash.find(botid, rule)
        if wash is not None:
            if kwargs.get('replace'): wash.replace = kwargs.get('replace')
            if kwargs.get('status'): wash.status = kwargs.get('status')
            if kwargs.get('remark'): wash.remark = kwargs.get('remark')
            wash.query.session.commit()
        return wash

    @staticmethod
    def findall(botid):
        return SpeakWash.query.filter_by(botid = botid).all()

    @staticmethod
    def find(botid, rule):
        return SpeakWash.query.filter_by(botid = botid, rule = rule).first()

    @staticmethod
    def delete(botid, rule):
        SpeakWash.query.filter_by(botid = botid, rule = rule).delete()
        SpeakWash.query.session.commit()
        return True

    @staticmethod
    def do(botid, text):
        washlist = SpeakWash.findall(botid)
        for wash in washlist:
            p = re.compile(r'' + wash.rule)
            text = p.sub(r'' + wash.replace, text)
        return text


# todo 实现计划调度自动计算speak count
@pr.register_model(40)
class SpeakCount(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'speak_count'

    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    botid = db.Column(db.String(20), nullable = False)
    target = db.Column(db.String(20), nullable = False)
    sender_id = db.Column(db.String(20), nullable = False)
    sender_name = db.Column(db.String(20), nullable = False)
    date = db.Column(db.Date, nullable = False)
    message_count = db.Column(db.Integer, nullable = False)
    vaild_count = db.Column(db.Integer, nullable = False)

    __table_args__ = (UniqueConstraint('botid', 'target', 'sender_id', 'date', name = 'speak_daily_count_uc'),)

    @staticmethod
    def do(botid, target_type, target_account, date):
        target = get_target_value(target_type, target_account)
        session = sessionmaker(bind = db.get_engine(bind = 'score'))()
        try:
            session.execute(
                'INSERT INTO speak_count(botid,target,sender_id,sender_name,date,message_count,vaild_count) '
                'SELECT t1.botid,t1.target,t1.sender_id,t1.sender_name,t1.date,'
                'SUM(1) message_count,SUM(CASE WHEN t1.washed_chars < t2.value THEN 0 ELSE 1 END) vaild_count '
                'FROM speak t1 LEFT JOIN bot_param t2 ON t1.botid=t2.botid AND t2.name="baseline" '
                'WHERE t1.botid = :botid AND t1.target = :target AND t1.date = :date '
                'GROUP BY t1.botid,t1.target,t1.sender_id,t1.date',
                {'botid': botid, 'target': target, 'date': date})
            session.commit()
        except IntegrityError as e:
            raise Exception(date + '已执行过此任务')
        except Exception as e:
            raise e

        return True


db.create_all()


# View-----------------------------------------------------------------------------------------------------
@pr.register_view()
class SpeakView(CVAdminModelView):
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 100
    column_filters = ('target', 'sender_id', 'sender_name', 'date', 'washed_chars')
    column_list = (
        'botid', 'target', 'sender', 'date', 'time', 'message', 'washed_text', 'washed_chars')
    column_searchable_list = ('sender_name', 'message')
    column_labels = dict(botid = '机器人', target = '目标',
                         sender = '成员', sender_id = '成员账号', sender_name = '成员名称',
                         date = '日期', time = '时间',
                         message = '消息原文', washed_text = '有效消息内容', washed_chars = '有效消息字数')
    # column_formatters = dict(date=lambda v, c, m, p: datetime.fromtimestamp(m.create_at).strftime('%Y-%m-%d'),
    #                          time=lambda v, c, m, p: datetime.fromtimestamp(m.update_at).strftime('%Y-%m-%d'))
    column_formatters = dict(botid = lambda v, c, m, p: get_botname(m.botid),
                             target = lambda v, c, m, p: get_target_display(m.target),
                             sender = lambda v, c, m, p: m.sender_id + ' : ' + get_omit_display(m.sender_name),
                             date = lambda v, c, m, p: display_datetime(m.create_at, False),
                             time = lambda v, c, m, p: m.time.strftime('%H:%M'),
                             message = lambda v, c, m, p: get_omit_display(m.message),
                             washed_text = lambda v, c, m, p: get_omit_display(m.washed_text))

    column_default_sort = ('id', True)

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '消息记录', '消息管理')

    def get_query(self):
        from flask_login import current_user
        if not current_user.is_admin():
            return super(SpeakView, self).get_query().filter(self.model.botid == current_user.username)
        else:
            return super(SpeakView, self).get_query()

    def get_count_query(self):
        from flask_login import current_user
        from flask_admin.contrib.sqla.view import func
        if not current_user.is_admin():
            return self.session.query(func.count('*')).filter(self.model.botid == current_user.username)
        else:
            return super(SpeakView, self).get_count_query()


# todo edit form优化状态显示
# todo 支持create
@pr.register_view()
class SpeakWashView(CVAdminModelView):
    column_filters = ('status',)
    column_labels = dict(id = '规则ID', botid = '机器人', rule = '匹配规则', replace = '清洗结果', status = '状态',
                         create_at = '创建时间', update_at = '更新时间', remark = '备注')
    column_formatters = dict(botid = lambda v, c, m, p: get_botname(m.botid),
                             status = lambda v, c, m, p: '启用' if m.status == 1 else '禁用',
                             create_at = lambda v, c, m, p: display_datetime(m.create_at),
                             update_at = lambda v, c, m, p: display_datetime(m.update_at))

    form_create_rules = (
        rules.FieldSet(('botid', 'active', 'remark'), '基本信息'),
        rules.FieldSet(('rule', 'replace'), '规则设置')
    )

    form_edit_rules = (
        rules.FieldSet(('botid', 'active', 'remark'), '基本信息'),
        rules.FieldSet(('rule', 'replace'), '规则设置')
    )

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '发言清洗规则', '机器人设置')

    def get_query(self):
        from flask_login import current_user
        if not current_user.is_admin():
            return super(SpeakWashView, self).get_query().filter(self.model.botid == current_user.username)
        else:
            return super(SpeakWashView, self).get_query()

    def get_count_query(self):
        from flask_login import current_user
        from flask_admin.contrib.sqla.view import func
        if not current_user.is_admin():
            return self.session.query(func.count('*')).filter(self.model.botid == current_user.username)
        else:
            return super(SpeakWashView, self).get_count_query()

    def get_create_form(self):
        form = self.scaffold_form()
        form.botid = fields.StringField('机器人ID', [validators.required(message = '机器人ID是必填字段')])
        form.rule = fields.StringField('匹配规则', [validators.required(message = '匹配规则是必填字段')])
        form.replace = fields.StringField('清洗结果', [validators.required(message = '清洗结果是必填字段')])
        form.active = fields.BooleanField('启用状态')
        form.remark = fields.StringField('备注')
        return form

    def get_edit_form(self):
        form = self.scaffold_form()
        form.botid = fields.StringField('机器人ID', [validators.required(message = '机器人ID是必填字段')])
        form.rule = fields.StringField('匹配规则', [validators.required(message = '匹配规则是必填字段')])
        form.replace = fields.StringField('清洗结果', [validators.required(message = '清洗结果是必填字段')])
        form.active = fields.BooleanField('启用状态')
        form.remark = fields.StringField('备注')
        return form


@pr.register_view()
class SpeakCountView(CVAdminModelView):
    can_edit = False
    column_filters = ('sender_id', 'sender_name', 'date', 'message_count', 'vaild_count')
    column_list = ('botid', 'target', 'sender', 'date', 'message_count', 'vaild_count')
    column_labels = dict(botid = '机器人', target = '目标',
                         sender = '成员', sender_id = '成员账号', sender_name = '成员名称',
                         date = '日期', message_count = '消息总数', vaild_count = '有效消息总数')
    column_formatters = dict(
        botid = lambda v, c, m, p: get_botname(m.botid),
        target = lambda v, c, m, p: get_target_display(m.target),
        sender = lambda v, c, m, p: m.sender_id + ' : ' + get_omit_display(m.sender_name),
        date = lambda v, c, m, p: m.date.strftime('%Y-%m-%d'))

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '发言统计', '统计分析')

    def get_query(self):
        from flask_login import current_user
        if not current_user.is_admin():
            return super(SpeakCountView, self).get_query().filter(self.model.botid == current_user.username)
        else:
            return super(SpeakCountView, self).get_query()

    def get_count_query(self):
        from flask_login import current_user
        from flask_admin.contrib.sqla.view import func
        if not current_user.is_admin():
            return self.session.query(func.count('*')).filter(self.model.botid == current_user.username)
        else:
            return super(SpeakCountView, self).get_count_query()


# Control--------------------------------------------------------------------------------------------------
@ac.register_api('/speakrecord', endpoint = 'speakrecord')
class SpeakRecordAPI(Resource):
    method_decorators = [ac.require_apikey]

    def post(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('target_type', required = True, help = '请求中必须包含target_type')
            parser.add_argument('target_account', required = True, help = '请求中必须包含target_account')
            parser.add_argument('sender_id', required = True, help = '请求中必须包含sender_id')
            parser.add_argument('sender_name')
            parser.add_argument('date')
            parser.add_argument('time')
            parser.add_argument('create_at')
            parser.add_argument('message', required = True, help = '请求中必须包含message')
            args = parser.parse_args()
            record = Speak.create(ac.get_bot(),
                                  args['target_type'],
                                  args['target_account'],
                                  args['sender_id'],
                                  args['message'],
                                  sender_name = args['sender_name'])
            if record is not None:
                return ac.success(botid = record.botid,
                                  target = record.target,
                                  sender_id = record.sender_id,
                                  sender_name = record.sender_name,
                                  date = record.date,
                                  time = record.time,
                                  create_at = record.create_at,
                                  message = record.message,
                                  washed_text = record.washed_text,
                                  washed_chars = record.washed_chars)
            else:
                return ac.fault(error = Exception('未知原因导致数据创建失败'))
        except Exception as e:
            return ac.fault(error = e)


@ac.register_api('/speakwashs', endpoint = 'speakwashs')
class SpeakWashsAPI(Resource):
    method_decorators = [ac.require_apikey]

    def get(self):
        try:
            rules = SpeakWash.findall(ac.get_bot())
            result = []
            for rule in rules:
                result.append({'botid': rule.botid,
                               'rule': rule.rule,
                               'replace': rule.replace,
                               'status': rule.status,
                               'create_at': rule.create_at.strftime('%Y-%m-%d %H:%M'),
                               'update_at': rule.update_at.strftime('%Y-%m-%d %H:%M'),
                               'remark': rule.remark})
            return ac.success(rules = result)
        except Exception as e:
            return ac.fault(error = e)


@ac.register_api('/speakwash', endpoint = 'speakwash')
class SpeakWashAPI(Resource):
    method_decorators = [ac.require_apikey]

    def put(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('rule', required = True, help = '请求中必须包含rule')
            parser.add_argument('replace', required = True, help = '请求中必须包含replace')
            parser.add_argument('remark')
            args = parser.parse_args()
            rule = SpeakWash.create(ac.get_bot(), args['rule'], args['replace'], args['remark'])
            if rule is not None:
                return ac.success(botid = rule.botid,
                                  rule = rule.rule,
                                  replace = rule.replace,
                                  status = rule.status,
                                  create_at = rule.create_at.strftime('%Y-%m-%d %H:%M'),
                                  update_at = rule.update_at.strftime('%Y-%m-%d %H:%M'),
                                  remark = rule.remark)
            else:
                return ac.fault(error = Exception('未知原因导致数据创建失败'))
        except Exception as e:
            return ac.fault(error = e)

    def patch(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('rule', required = True, help = '请求中必须包含rule')
            parser.add_argument('replace')
            parser.add_argument('status')
            parser.add_argument('remark')
            args = parser.parse_args()
            rule = SpeakWash.update(ac.get_bot(),
                                    args['rule'],
                                    replace = args['replace'],
                                    status = args['status'],
                                    remark = args['remark'])
            if rule is not None:
                return ac.success(botid = rule.botid,
                                  rule = rule.rule,
                                  replace = rule.replace,
                                  status = rule.status,
                                  create_at = rule.create_at.strftime('%Y-%m-%d %H:%M'),
                                  update_at = rule.update_at.strftime('%Y-%m-%d %H:%M'),
                                  remark = rule.remark)
            else:
                return ac.fault(error = Exception(ac.get_bot() + '未找到名称为' + args['name'] + '的参数'))
        except Exception as e:
            return ac.fault(error = e)

    def get(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('rule', required = True, help = '请求中必须包含rule')
            args = parser.parse_args()
            rule = SpeakWash.find(ac.get_bot(), args['rule'])
            if rule is not None:
                return ac.success(botid = rule.botid,
                                  rule = rule.rule,
                                  replace = rule.replace,
                                  status = rule.status,
                                  create_at = rule.create_at.strftime('%Y-%m-%d %H:%M'),
                                  update_at = rule.update_at.strftime('%Y-%m-%d %H:%M'),
                                  remark = rule.remark)
            else:
                return ac.fault(error = Exception(ac.get_bot() + '未找到名称为' + args['name'] + '的参数'))
        except Exception as e:
            return ac.fault(error = e)

    def delete(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('rule', required = True, help = '请求中必须包含rule')
            args = parser.parse_args()
            result = SpeakWash.delete(ac.get_bot(), args['rule'])
            if result is not None:
                return ac.success(botid = ac.get_bot(), rule = args['rule'])
            else:
                return ac.fault(error = Exception('未知原因导致数据删除失败'))
        except Exception as e:
            return ac.fault(error = e)


@ac.register_api('/speakwashdo', endpoint = 'speakwashdo')
class SpeakWashDoAPI(Resource):
    method_decorators = [ac.require_apikey]

    def patch(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('id', required = True, help = '请求中必须包含id')
            args = parser.parse_args()
            record = Speak.dowash(args['id'])
            if record is not None:
                return ac.success(botid = record.botid,
                                  target = record.target,
                                  sender_id = record.sender_id,
                                  sender_name = record.sender_name,
                                  date = record.date,
                                  time = record.time,
                                  create_at = record.create_at,
                                  message = record.message,
                                  washed_text = record.washed_text,
                                  washed_chars = record.washed_chars)
            else:
                return ac.fault(error = Exception('未知原因导致数据创建失败'))
        except Exception as e:
            return ac.fault(error = e)


@ac.register_api('/speakwashupdate', endpoint = 'speakwashupdate')
class SpeakWashUpdateAPI(Resource):
    method_decorators = [ac.require_apikey]

    def patch(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('target_type', required = True, help = '请求中必须包含target_type')
            parser.add_argument('target_account', required = True, help = '请求中必须包含target_account')
            parser.add_argument('date_from', required = True, help = '请求中必须包含date_from')
            parser.add_argument('date_to', required = True, help = '请求中必须包含date_to')
            args = parser.parse_args()
            result = Speak.updatewash(ac.get_bot(),
                                      args['target_type'],
                                      args['target_account'],
                                      args['date_from'],
                                      args['date_to'])
            if result is not None:
                return ac.success(update_count = result)
            else:
                return ac.fault(error = Exception('未知原因导致数据创建失败'))
        except Exception as e:
            return ac.fault(error = e)


@ac.register_api('/speaktop', endpoint = 'speaktop')
class SpeakTopAPI(Resource):
    method_decorators = [ac.require_apikey]

    def get(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('target_type', required = True, help = '请求中必须包含target_type')
            parser.add_argument('target_account', required = True, help = '请求中必须包含target_account')
            parser.add_argument('date_from', required = True, help = '请求中必须包含date_from')
            parser.add_argument('date_to', required = True, help = '请求中必须包含date_to')
            parser.add_argument('limit', type = int)
            parser.add_argument('is_valid', type = int)
            args = parser.parse_args()
            records = Speak.get_top(ac.get_bot(),
                                    args['target_type'],
                                    args['target_account'],
                                    args['date_from'],
                                    args['date_to'],
                                    args['limit'] if args.get('limit', None) is not None else 10,
                                    True if args.get('is_valid', 0) == 1 else False)
            result = []
            for record in records:
                result.append({'sender_id': record.sender_id,
                               'sender_name': record.sender_name,
                               'count': record.cnt})
            return ac.success(target_type = args['target_type'],
                              target_account = args['target_account'],
                              date_from = args['date_from'],
                              date_to = args['date_to'],
                              limit = args['limit'],
                              is_valid = args['is_valid'],
                              toprank = result)
        except Exception as e:
            return ac.fault(error = e)


@ac.register_api('/speakcount', endpoint = 'speakcount')
class SpeakCountAPI(Resource):
    method_decorators = [ac.require_apikey]

    def get(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('target_type', required = True, help = '请求中必须包含target_type')
            parser.add_argument('target_account', required = True, help = '请求中必须包含target_account')
            parser.add_argument('sender', required = True, help = '请求中必须包含sender_id或sender_name')
            parser.add_argument('date_from', required = True, help = '请求中必须包含date_from')
            parser.add_argument('date_to', required = True, help = '请求中必须包含date_to')

            args = parser.parse_args()
            record = Speak.get_count(ac.get_bot(),
                                     args['target_type'],
                                     args['target_account'],
                                     args['date_from'],
                                     args['date_to'],
                                     args['sender'])
            if record is not None:
                return ac.success(target_type = args['target_type'],
                                  target_account = args['target_account'],
                                  sender = args['sender'],
                                  date_from = args['date_from'],
                                  date_to = args['date_to'],
                                  count_full = record.cnt_full if record.cnt_full is not None else 0,
                                  count_valid = record.cnt_valid if record.cnt_valid is not None else 0)
            else:
                return ac.fault(error = Exception('未知原因导致数据统计失败'))
        except Exception as e:
            return ac.fault(error = e)


@ac.register_api('/speaktotal', endpoint = 'speaktotal')
class SpeakTotalAPI(Resource):
    method_decorators = [ac.require_apikey]

    def get(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('target_type', required = True, help = '请求中必须包含target_type')
            parser.add_argument('target_account', required = True, help = '请求中必须包含target_account')
            parser.add_argument('date_from', required = True, help = '请求中必须包含date_from')
            parser.add_argument('date_to', required = True, help = '请求中必须包含date_to')

            args = parser.parse_args()
            record = Speak.get_count(ac.get_bot(),
                                     args['target_type'],
                                     args['target_account'],
                                     args['date_from'],
                                     args['date_to'])
            if record is not None:
                return ac.success(target_type = args['target_type'],
                                  target_account = args['target_account'],
                                  date_from = args['date_from'],
                                  date_to = args['date_to'],
                                  count_full = record.cnt_full if record.cnt_full is not None else 0,
                                  count_valid = record.cnt_valid if record.cnt_valid is not None else 0)
            else:
                return ac.fault(error = Exception('未知原因导致数据统计失败'))
        except Exception as e:
            return ac.fault(error = e)


@ac.register_api('/speakdailycount', endpoint = 'speakdailycount')
class SpeakCountAPI(Resource):
    method_decorators = [ac.require_apikey]

    def get(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('target_type', required = True, help = '请求中必须包含target_type')
            parser.add_argument('target_account', required = True, help = '请求中必须包含target_account')
            parser.add_argument('date', required = True, help = '请求中必须包含date')

            args = parser.parse_args()
            result = SpeakCount.do(ac.get_bot(),
                                   args['target_type'],
                                   args['target_account'],
                                   args['date'])
            if result:
                return ac.success(target_type = args['target_type'],
                                  target_account = args['target_account'],
                                  date = args['date'])
            else:
                return ac.fault(error = Exception('未知原因导致数据操作失败'))
        except Exception as e:
            return ac.fault(error = e)