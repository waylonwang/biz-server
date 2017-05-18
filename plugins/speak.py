import re
from datetime import datetime

from flask_restful import reqparse, Resource
from pytz import utc, timezone
from sqlalchemy import func, desc, case

import api_control as ac
import db_control
from app_view import CVAdminModelView
from plugin import PluginsRegistry

__registry__ = cr = PluginsRegistry()

# Model----------------------------------------------------------------------------------------------------
db = db_control.get_db()
api = ac.get_api()


class Speak(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'speak'

    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    botid = db.Column(db.String(20), nullable = False)
    target = db.Column(db.String(20), nullable = False)
    sender_id = db.Column(db.String(20), nullable = False)
    sender_name = db.Column(db.String(20), nullable = False)
    date = db.Column(db.String(20), nullable = False)
    time = db.Column(db.String(20), nullable = False)
    timemark = db.Column(db.Integer, nullable = False, default = int(datetime.now(tz = utc).timestamp()))
    message = db.Column(db.String(20), nullable = False)
    washed_text = db.Column(db.String(20), nullable = False)
    washed_chars = db.Column(db.Integer, nullable = False)

    target_map = {'group': 'g', 'discuzz': 'd', 'private': 'p'}

    @staticmethod
    def create(botid, target_type, target_account, sender_id, message, **kwargs):
        target = Speak.target_map.get(target_type) + '#' + target_account
        washed_text = SpeakWash.do(botid, message)
        record = Speak(botid = botid,
                       target = target,
                       sender_id = sender_id,
                       sender_name = '' if kwargs.get('sender_name') == None else kwargs.get('sender_name'),
                       date = datetime.now(tz = timezone('Asia/Shanghai')).strftime('%Y-%m-%d') if kwargs.get(
                           'date') == None else kwargs.get('date'),
                       time = datetime.now(tz = timezone('Asia/Shanghai')).strftime('%H:%M') if kwargs.get(
                           'time') == None else kwargs.get('time'),
                       timemark = int(datetime.now(tz = utc).timestamp()) if kwargs.get(
                           'timemark') == None else kwargs.get('timemark'),
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
        target = Speak.target_map.get(target_type) + '#' + target_account
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
        target = Speak.target_map.get(target_type) + '#' + target_account
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
        target = Speak.target_map.get(target_type) + '#' + target_account
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


class SpeakWash(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'speak_wash'

    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    botid = db.Column(db.String(20), nullable = False)
    rule = db.Column(db.String(200), nullable = False)
    replace = db.Column(db.String(200), nullable = False)
    status = db.Column(db.Integer, nullable = False)
    createtime = db.Column(db.Integer, nullable = False, default = int(datetime.now(tz = utc).timestamp()))
    updatetime = db.Column(db.Integer, nullable = False, default = int(datetime.now(tz = utc).timestamp()))
    remark = db.Column(db.String(255), nullable = True)

    @staticmethod
    def create(botid, rule, replace, remark):
        wash = SpeakWash.find(botid, rule)
        if wash == None:
            wash = SpeakWash(botid = botid,
                             rule = rule,
                             replace = replace,
                             status = 1,
                             createtime = int(datetime.now(tz = utc).timestamp()),
                             updatetime = int(datetime.now(tz = utc).timestamp()),
                             remark = remark)
            wash.query.session.add(wash)
            wash.query.session.commit()
        else:
            wash = SpeakWash.update(botid, rule, replace = replace, remark = remark)
        return wash

    @staticmethod
    def update(botid, rule, **kwargs):
        wash = SpeakWash.find(botid, rule)
        if wash != None:
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


class SpeakCount(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'speak_count'

    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    botid = db.Column(db.String(20), nullable = False)
    target = db.Column(db.String(20), nullable = False)
    sender_id = db.Column(db.String(20), nullable = False)
    sender_name = db.Column(db.String(20), nullable = False)
    date = db.Column(db.String(20), nullable = False)
    message_count = db.Column(db.Integer, nullable = False)
    vaild_count = db.Column(db.Integer, nullable = False)


db.create_all()


@cr.model('10-Speak')
def get_Speak_model():
    return Speak


@cr.model('73-SpeakWash')
def get_SpeakWash_model():
    return SpeakWash


@cr.model('40-SpeakCount')
def get_SpeakCount_model():
    return SpeakCount


# View-----------------------------------------------------------------------------------------------------
class SpeakView(CVAdminModelView):
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 100
    column_filters = ('target', 'sender_id', 'sender_name', 'date', 'washed_chars')
    column_list = (
        'botid', 'target', 'sender_id', 'sender_name', 'date', 'time', 'message', 'washed_text', 'washed_chars')
    column_searchable_list = ('sender_name', 'message')
    column_labels = dict(botid = '机器人ID', target = '目标',
                         sender_id = '发送者QQ', sender_name = '发送者名称',
                         date = '日期', time = '时间',
                         message = '消息原文', washed_text = '有效消息内容', washed_chars = '有效消息字数')
    # column_formatters = dict(date=lambda v, c, m, p: datetime.fromtimestamp(m.createtime).strftime('%Y-%m-%d'),
    #                          time=lambda v, c, m, p: datetime.fromtimestamp(m.updatetime).strftime('%Y-%m-%d'))
    column_formatters = dict(target = lambda v, c, m, p: _format_target(m.target),
                             sender_name = lambda v, c, m, p: str(m.sender_name)[0:10] + '...' if len(
                                 str(m.sender_name)) > 10 else str(m.sender_name)[0:10],
                             message = lambda v, c, m, p: str(m.message)[0:10] + '...' if len(
                                 str(m.message)) > 10 else str(m.message)[0:10],
                             washed_text = lambda v, c, m, p: str(m.washed_text)[0:10] + '...' if len(
                                 str(m.washed_text)) > 10 else str(m.washed_text)[0:10])

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '消息记录')

    def get_query(self):
        from flask_login import current_user
        if current_user.username != 'admin':
            return super(SpeakView, self).get_query().filter(self.model.botid == current_user.username)
        else:
            return super(SpeakView, self).get_query()

    def get_count_query(self):
        from flask_login import current_user
        from flask_admin.contrib.sqla.view import func
        if current_user.username != 'admin':
            return self.session.query(func.count('*')).filter(self.model.botid == current_user.username)
        else:
            return super(SpeakView, self).get_count_query()


class SpeakWashView(CVAdminModelView):
    column_filters = ('status',)
    column_labels = dict(id = '规则ID', botid = '机器人ID', rule = '匹配规则', replace = '清洗结果', status = '状态',
                         createtime = '创建时间', updatetime = '更新时间', remark = '备注')
    column_formatters = dict(status = lambda v, c, m, p: '启用' if m.status == 1 else '禁用',
                             createtime = lambda v, c, m, p: datetime.fromtimestamp(m.createtime).strftime('%Y-%m-%d'),
                             updatetime = lambda v, c, m, p: datetime.fromtimestamp(m.updatetime).strftime('%Y-%m-%d'))

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '发言清洗', '机器人设置')

    def get_query(self):
        from flask_login import current_user
        if current_user.username != 'admin':
            return super(SpeakWashView, self).get_query().filter(self.model.botid == current_user.username)
        else:
            return super(SpeakWashView, self).get_query()

    def get_count_query(self):
        from flask_login import current_user
        from flask_admin.contrib.sqla.view import func
        if current_user.username != 'admin':
            return self.session.query(func.count('*')).filter(self.model.botid == current_user.username)
        else:
            return super(SpeakWashView, self).get_count_query()


class SpeakCountView(CVAdminModelView):
    column_filters = ('sender_id', 'sender_name', 'date', 'message_count', 'vaild_count')
    column_list = ('botid', 'target', 'sender_id', 'sender_name', 'date', 'message_count', 'vaild_count')
    column_labels = dict(botid = '机器人ID', target = '目标', sender_id = '发送者QQ', sender_name = '发送者名称',
                         date = '日期', message_count = '消息总数', vaild_count = '有效消息总数')
    column_formatters = dict(
        sender_name = lambda v, c, m, p: str(m.sender_name)[0:10] + '...' if len(str(m.sender_name)) > 10 else str(
            m.sender_name)[0:10],
        date = lambda v, c, m, p: datetime.fromtimestamp(m.createtime).strftime('%Y-%m-%d'))

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '发言统计', '统计分析')

    def get_query(self):
        from flask_login import current_user
        if current_user.username != 'admin':
            return super(SpeakCountView, self).get_query().filter(self.model.botid == current_user.username)
        else:
            return super(SpeakCountView, self).get_query()

    def get_count_query(self):
        from flask_login import current_user
        from flask_admin.contrib.sqla.view import func
        if current_user.username != 'admin':
            return self.session.query(func.count('*')).filter(self.model.botid == current_user.username)
        else:
            return super(SpeakCountView, self).get_count_query()


@cr.view('10-Speak')
def get_Speak_view():
    return SpeakView


@cr.view('73-SpeakWash')
def get_SpeakWash_view():
    return SpeakWashView


@cr.view('40-SpeakCount')
def get_SpeakCount_view():
    return SpeakCountView


def _format_target(text):
    return text.replace('g#', '群:').replace('d#', '组:').replace('p#', '单聊:')


# Control--------------------------------------------------------------------------------------------------
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
            parser.add_argument('timemark')
            parser.add_argument('message', required = True, help = '请求中必须包含message')
            args = parser.parse_args()
            record = Speak.create(ac.get_bot(),
                                  args['target_type'],
                                  args['target_account'],
                                  args['sender_id'],
                                  args['message'],
                                  sender_name = args['sender_name'],
                                  date = args['date'],
                                  time = args['time'],
                                  timemark = args['timemark'])
            if record is not None:
                return ac.success(botid = record.botid,
                                  target = record.target,
                                  sender_id = record.sender_id,
                                  sender_name = record.sender_name,
                                  date = record.date,
                                  time = record.time,
                                  timemark = record.timemark,
                                  message = record.message,
                                  washed_text = record.washed_text,
                                  washed_chars = record.washed_chars)
            else:
                return ac.fault(error = Exception('未知原因导致数据创建失败'))
        except Exception as e:
            return ac.fault(error = e)


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
                               'createtime': rule.createtime,
                               'updatetime': rule.updatetime,
                               'remark': rule.remark})
            return ac.success(rules = result)
        except Exception as e:
            return ac.fault(error = e)


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
                                  createtime = rule.createtime,
                                  updatetime = rule.updatetime,
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
                                  createtime = rule.createtime,
                                  updatetime = rule.updatetime,
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
                                  createtime = rule.createtime,
                                  updatetime = rule.updatetime,
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


class SpeakWashDoAPI(Resource):
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
                                  timemark = record.timemark,
                                  message = record.message,
                                  washed_text = record.washed_text,
                                  washed_chars = record.washed_chars)
            else:
                return ac.fault(error = Exception('未知原因导致数据创建失败'))
        except Exception as e:
            return ac.fault(error = e)


class SpeakWashUpdateAPI(Resource):
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


class SpeakTopAPI(Resource):
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


class SpeakCountAPI(Resource):
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
        except Exception as e:
            return ac.fault(error = e)


class SpeakTotalAPI(Resource):
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
        except Exception as e:
            return ac.fault(error = e)


api.add_resource(SpeakRecordAPI, '/speakrecord', endpoint = 'speakrecord')
api.add_resource(SpeakWashsAPI, '/speakwashs', endpoint = 'speakwashs')
api.add_resource(SpeakWashAPI, '/speakwash', endpoint = 'speakwash')
api.add_resource(SpeakWashDoAPI, '/speakwashdo', endpoint = 'speakwashdo')
api.add_resource(SpeakWashUpdateAPI, '/speakwashupdate', endpoint = 'speakwashupdate')
api.add_resource(SpeakTopAPI, '/speaktop', endpoint = 'speaktop')
api.add_resource(SpeakCountAPI, '/speakcount', endpoint = 'speakcount')
api.add_resource(SpeakTotalAPI, '/speaktotal', endpoint = 'speaktotal')