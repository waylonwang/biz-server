import re
from datetime import datetime, timedelta

import math
from flask import request, redirect, json
from flask_admin import expose
from flask_admin.form import rules, FormOpts, Select2Widget, DatePickerWidget
from flask_admin.helpers import get_redirect_target, validate_form_on_submit
from flask_restful import reqparse, Resource
from sqlalchemy import func, desc, case, UniqueConstraint, bindparam
from sqlalchemy.orm import sessionmaker
from wtforms import validators, fields, HiddenField

import api_control as ac
import db_control
from app_view import CVAdminModelView
from common.basedata import Basedata
from common.bot import bot_registry
from common.util import get_now, display_datetime, get_botname, get_target_composevalue, get_target_display,\
    get_list_by_botassign, get_list_count_by_botassign, target_prefix2name, output_datetime, get_CQ_display
from plugin import PluginsRegistry

__registry__ = pr = PluginsRegistry()

br = bot_registry()

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
    date = db.Column(db.Date, nullable = False, default = lambda: get_now(), index = True)
    time = db.Column(db.Time, nullable = False, default = lambda: datetime.time(get_now()), index = True)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    update_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now())
    message = db.Column(db.String(20), nullable = False)
    washed_text = db.Column(db.String(20), nullable = False)
    washed_chars = db.Column(db.Integer, nullable = False)

    @staticmethod
    def create(botid, target_type, target_account, sender_id, message, **kwargs):
        target = get_target_composevalue(target_type, target_account)
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
        start = get_now()
        records = Speak.find_by_date(botid, target_type, target_account, date_from, date_to)
        # texts = {record.id: record.message for record in records}
        count = len(records)
        texts = {str(record.id) + '>>>END>>>' + record.message for record in records}
        text = '<<<BEGIN<<<'.join(texts)
        ws = SpeakWash.do(botid, text)

        data = []
        wl = ws.split('<<<BEGIN<<<')
        for ts in wl:
            tl = ts.split('>>>END>>>')
            data.append({'b_id': tl[0], 'washed_text': tl[1], 'washed_chars': len(tl[1])})

        speaktable = Speak.metadata.tables['speak']

        upt = speaktable.update().\
            where(speaktable.c.id == bindparam('b_id')).\
            values(washed_text = bindparam('washed_text'), washed_chars = bindparam('washed_chars'))

        conn = db.get_engine(bind = 'score').connect()
        conn.execute(upt, data)
        conn.close()

        duration = round((get_now() - start).total_seconds(), 1)

        return count, duration

    @staticmethod
    def find_by_date(botid, target_type, target_account, date_from, date_to):
        target = get_target_composevalue(target_type, target_account)
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
        target = get_target_composevalue(target_type, target_account)
        baseline = 0
        if is_valid:
            from plugins.setting import BotParam
            param = BotParam.find(botid, 'speak_valid_baseline')
            if param is not None:
                baseline = param.value

        return Speak.query.session.query(
            Speak.sender_id, Speak.sender_name, func.count(1).label('cnt')
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
        target = get_target_composevalue(target_type, target_account)
        baseline = 0
        from plugins.setting import BotParam
        param = BotParam.find(botid, 'speak_valid_baseline')
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

    @staticmethod
    def get_count(botid, target_type, target_account, date_from, date_to, sender = None):
        target = get_target_composevalue(target_type, target_account)
        baseline = 0
        from plugins.setting import BotParam
        param = BotParam.find(botid, 'speak_valid_baseline')
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
    rule = db.Column(db.String(20), nullable = False)
    # replace = db.Column(db.String(200), nullable = False)l
    surplus = db.Column(db.Integer, nullable = False, default = 0)
    status = db.Column(db.Integer, nullable = False, default = 1)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    update_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now())
    remark = db.Column(db.String(255), nullable = True)

    @staticmethod
    def create(botid, rule, surplus, remark):
        wash = SpeakWash.find(botid, rule)
        if wash is None:
            wash = SpeakWash(botid = botid,
                             rule = rule,
                             surplus = surplus,
                             status = 1,
                             remark = remark)
            wash.query.session.add(wash)
            wash.query.session.commit()
        else:
            wash = SpeakWash.update(botid, rule, surplus = surplus, remark = remark)
        return wash

    @staticmethod
    def update(botid, rule, **kwargs):
        wash = SpeakWash.find(botid, rule)
        if wash is not None:
            if kwargs.get('surplus'): wash.surplus = kwargs.get('surplus')
            if kwargs.get('status'): wash.status = kwargs.get('status')
            if kwargs.get('remark'): wash.remark = kwargs.get('remark')
            wash.query.session.commit()
        return wash

    @staticmethod
    def findall(botid):
        return SpeakWash.query.filter_by(botid = botid, status = 1).all()

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
            basedata = Basedata.find_by_code(wash.rule)
            rule = basedata.value
            replace = ''.join('_' * wash.surplus)
            p = re.compile(r'' + rule)
            text = p.sub(r'' + replace, text)
        return text

    @staticmethod
    @br.register_destroy()
    def destroy(botid):
        for r in SpeakWash.findall(botid):
            SpeakWash.delete(botid, r.rule)
        return True


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
    def do(botid, target_type, target_account, date_from, date_to):
        target = get_target_composevalue(target_type, target_account)
        session = sessionmaker(bind = db.get_engine(bind = 'score'))()
        try:
            session.execute(
                'DELETE FROM speak_count '
                'WHERE botid = :botid AND target = :target AND date >= :date_from AND date <= :date_to ',
                {'botid': botid, 'target': target, 'date_from': date_from, 'date_to': date_to})
            session.execute(
                'INSERT INTO speak_count(botid,target,sender_id,sender_name,date,message_count,vaild_count) '
                'SELECT t1.botid,t1.target,t1.sender_id,t1.sender_name,t1.date,'
                'SUM(1) message_count,SUM(CASE WHEN t1.washed_chars < t2.value THEN 0 ELSE 1 END) vaild_count '
                'FROM speak t1 LEFT JOIN bot_param t2 ON t1.botid=t2.botid AND t2.name="speak_valid_baseline" '
                'WHERE t1.botid = :botid AND t1.target = :target AND t1.date >= :date_from AND t1.date <= :date_to '
                'GROUP BY t1.botid,t1.target,t1.sender_id,t1.date',
                {'botid': botid, 'target': target, 'date_from': date_from, 'date_to': date_to})
            session.commit()
        # except IntegrityError as e:
        #     raise Exception(date_from + '到' + date_to + '期间已执行过此任务，部分数据处理失败')
        except Exception as e:
            raise e

        return True

    @staticmethod
    def statistics(botid, target_type, target_account, date_from, date_to):
        target = get_target_composevalue(target_type, target_account)
        session = sessionmaker(bind = db.get_engine(bind = 'score'))()
        try:
            return session.execute(
                'SELECT t1.botid,t1.target,t1.date,'
                'SUM(t1.message_count) message_count,SUM(t1.vaild_count) vaild_count '
                'FROM speak_count t1 '
                'WHERE t1.botid = :botid AND t1.target = :target AND t1.date >= :date_from AND t1.date <= :date_to '
                'GROUP BY t1.botid,t1.target,t1.date',
                {'botid': botid, 'target': target, 'date_from': date_from, 'date_to': date_to})
        except Exception as e:
            raise e


db.create_all()


# View-----------------------------------------------------------------------------------------------------
@pr.register_view()
class SpeakView(CVAdminModelView):
    list_template = 'model/listdo-speak.html'
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 100
    column_filters = ('target', 'sender_id', 'sender_name', 'date', 'washed_chars')
    column_list = (
        'botid', 'target', 'sender', 'date', 'time', 'message', 'washed_text', 'washed_chars')
    column_searchable_list = ('sender_name', 'message')
    column_labels = dict(id = 'ID', botid = '机器人', target = '目标',
                         sender = '成员', sender_id = '成员账号', sender_name = '成员名称',
                         date = '日期', time = '时间',
                         message = '消息原文', washed_text = '有效内容', washed_chars = '有效字数')
    # column_formatters = dict(date=lambda v, c, m, p: datetime.fromtimestamp(m.create_at).strftime('%Y-%m-%d'),
    #                          time=lambda v, c, m, p: datetime.fromtimestamp(m.update_at).strftime('%Y-%m-%d'))
    column_formatters = dict(botid = lambda v, c, m, p: get_botname(m.botid),
                             target = lambda v, c, m, p: get_target_display(m.target),
                             sender = lambda v, c, m, p: get_CQ_display(m.sender_id + ' : ' + m.sender_name),
                             message = lambda v, c, m, p: get_CQ_display(m.message),
                             date = lambda v, c, m, p: display_datetime(m.create_at, False),
                             time = lambda v, c, m, p: m.time.strftime('%H:%M'))

    column_default_sort = ('id', True)

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '消息记录', '消息管理')

    def get_query(self):
        return get_list_by_botassign(Speak, SpeakView, self)

    def get_count_query(self):
        return get_list_count_by_botassign(Speak, SpeakView, self)

    def get_action_form(self):
        '''
            定制Action
        :return: 
        '''

        def bot_query_factory():
            from flask_login import current_user
            from common.bot import BotAssign
            return [r.botid for r in BotAssign.find_by_user(current_user.username)]

        def bot_get_pk(obj):
            return obj

        def bot_get_label(obj):
            from common.bot import Bot
            return Bot.find(obj).name

        def target_query_factory():
            from flask_login import current_user
            from plugins.setting import TargetRule
            return [r.botid + '|' + r.target for r in TargetRule.find_allow_by_user(current_user.username)]

        def target_get_pk(obj):
            return obj

        def target_get_label(obj):
            return get_target_display(obj.split('|')[1])

        from wtforms.ext.sqlalchemy.fields import QuerySelectField

        class DoCountForm(self.form_base_class):
            form_widget_args = {}
            form_edit_rules = [
                rules.Field('botid'),
                rules.Field('target'),
                rules.Field('date_from'),
                rules.Field('date_to')
            ]
            _form_edit_rules = rules.RuleSet(self, form_edit_rules)
            action = HiddenField('')
            url = HiddenField('')

            botid = QuerySelectField('机器人', [validators.required(message = '机器人是必填字段')],
                                     query_factory = bot_query_factory, get_label = bot_get_label,
                                     get_pk = bot_get_pk, widget = Select2Widget())

            target = QuerySelectField('目标', [validators.required(message = '目标是必填字段')],
                                      query_factory = target_query_factory, get_label = target_get_label,
                                      get_pk = target_get_pk, widget = Select2Widget())

            date_from = fields.DateField('开始日期', [validators.required(message = '开始日期是必填字段')],
                                         widget = DatePickerWidget())
            date_to = fields.DateField('结束日期', [validators.required(message = '结束日期是必填字段')],
                                       widget = DatePickerWidget())

        return DoCountForm

    @expose('/do/', methods = ('GET', 'POST'))
    def do_view(self):
        """
            Reset password view
        """
        return_url = get_redirect_target() or self.get_url('.index_view')
        # return self.render('model/do.html',return_url = return_url)


        form = self.action_form()

        if validate_form_on_submit(form):
            result = Speak.updatewash(form.data.get('botid'),
                                      target_prefix2name(form.data.get('target').split('|')[1].split('#')[0]),
                                      form.data.get('target').split('|')[1].split('#')[1],
                                      str(form.data.get('date_from')),
                                      str(form.data.get('date_to')))
            # if result:
            return redirect(return_url)

        if not hasattr(form, '_validated_ruleset') or not form._validated_ruleset:
            self._validate_form_instance(ruleset = form._form_edit_rules, form = form)

        if self.validate_form(form):
            pass
            # if self.update_model(form, None):
            #     flash(gettext('Record was successfully saved.'), 'success')
            #     if '_add_another' in request.form:
            #         return redirect(self.get_url('.create_view', url = return_url))
            #     elif '_continue_editing' in request.form:
            #         return redirect(request.url)
            #     else:
            #         # save button
            #         return redirect(self.get_save_return_url(None, is_created = False))

        if request.method == 'GET' or form.errors:
            self.on_form_prefill(form, id)

        form_opts = FormOpts(widget_args = form.form_widget_args,
                             form_rules = form._form_edit_rules)

        template = 'model/do.html'

        return self.render(template,
                           model = None,
                           form = form,
                           form_opts = form_opts,
                           return_url = return_url,
                           brand = request.args.get('caption'))


@pr.register_view()
class SpeakWashView(CVAdminModelView):
    can_create = True
    can_delete = True
    column_filters = ('status',)
    column_labels = dict(id = '规则ID', botid = '机器人', rule = '匹配规则', surplus = '清洗余量', status = '状态',
                         create_at = '创建时间', update_at = '更新时间', remark = '备注')
    column_formatters = dict(botid = lambda v, c, m, p: get_botname(m.botid),
                             rule = lambda v, c, m, p: Basedata.find_by_code(m.rule).name,
                             status = lambda v, c, m, p: '启用' if m.status == 1 else '禁用',
                             create_at = lambda v, c, m, p: display_datetime(m.create_at),
                             update_at = lambda v, c, m, p: display_datetime(m.update_at))

    form_create_rules = (
        rules.FieldSet(('botid', 'status', 'remark'), '基本信息'),
        rules.FieldSet(('rule', 'surplus'), '规则设置')
    )

    form_edit_rules = (
        rules.FieldSet(('botid', 'status', 'remark'), '基本信息'),
        rules.FieldSet(('rule', 'surplus'), '规则设置')
    )

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '发言清洗规则', '机器人设置')

    def get_query(self):
        return get_list_by_botassign(SpeakWash, SpeakWashView, self)

    def get_count_query(self):
        return get_list_count_by_botassign(SpeakWash, SpeakWashView, self)

    def get_create_form(self):
        form = self.scaffold_form()

        def bot_query_factory():
            from flask_login import current_user
            from common.bot import BotAssign
            return [r.botid for r in BotAssign.find_by_user(current_user.username)]

        def bot_get_pk(obj):
            return obj

        def bot_get_label(obj):
            from common.bot import Bot
            return Bot.find(obj).name

        from wtforms.ext.sqlalchemy.fields import QuerySelectField
        form.botid = QuerySelectField('机器人', [validators.required(message = '机器人是必填字段')],
                                      query_factory = bot_query_factory, get_label = bot_get_label, get_pk = bot_get_pk,
                                      widget = Select2Widget())

        # form.botid = fields.StringField('机器人ID', [validators.required(message = '机器人ID是必填字段')])

        def rule_query_factory():
            return [r.code for r in Basedata.find_by_type(2)]

        def rule_get_pk(obj):
            return obj

        def rule_get_label(obj):
            return Basedata.find_by_code(obj).name

        form.rule = QuerySelectField('匹配规则', [validators.required(message = '匹配规则是必填字段')],
                                     query_factory = rule_query_factory, get_label = rule_get_label,
                                     get_pk = rule_get_pk, widget = Select2Widget())
        form.surplus = fields.IntegerField('清洗余量', [validators.InputRequired(message = '清洗余量是必填字段')])
        form.status = fields.BooleanField('启用状态', default = True)
        form.remark = fields.StringField('备注')
        return form

    def get_edit_form(self):
        form = self.scaffold_form()

        def bot_query_factory():
            from flask_login import current_user
            from common.bot import BotAssign
            return [r.botid for r in BotAssign.find_by_user(current_user.username)]

        def bot_get_pk(obj):
            return obj

        def bot_get_label(obj):
            from common.bot import Bot
            return Bot.find(obj).name

        from wtforms.ext.sqlalchemy.fields import QuerySelectField
        form.botid = QuerySelectField('机器人', [validators.required(message = '机器人是必填字段')],
                                      query_factory = bot_query_factory, get_label = bot_get_label, get_pk = bot_get_pk,
                                      widget = Select2Widget())

        def rule_query_factory():
            return [r.code for r in Basedata.find_by_type(2)]

        def rule_get_pk(obj):
            return obj

        def rule_get_label(obj):
            return Basedata.find_by_code(obj).name

        form.rule = QuerySelectField('匹配规则', [validators.required(message = '匹配规则是必填字段')],
                                     query_factory = rule_query_factory, get_label = rule_get_label,
                                     get_pk = rule_get_pk, widget = Select2Widget())
        form.surplus = fields.IntegerField('清洗余量', [validators.InputRequired(message = '清洗余量是必填字段')])
        form.status = fields.BooleanField('启用状态', default = True)
        form.remark = fields.StringField('备注')
        return form


@pr.register_view()
class SpeakCountView(CVAdminModelView):
    list_template = 'model/listdo-speakcount.html'
    can_edit = False
    column_filters = ('sender_id', 'sender_name', 'date', 'message_count', 'vaild_count')
    column_list = ('botid', 'target', 'sender', 'date', 'message_count', 'vaild_count')
    column_labels = dict(botid = '机器人', target = '目标',
                         sender = '成员', sender_id = '成员账号', sender_name = '成员名称',
                         date = '日期', message_count = '消息总数', vaild_count = '有效消息总数')
    column_formatters = dict(
        botid = lambda v, c, m, p: get_botname(m.botid),
        target = lambda v, c, m, p: get_target_display(m.target),
        sender = lambda v, c, m, p: get_CQ_display(m.sender_id + ' : ' + m.sender_name),
        date = lambda v, c, m, p: m.date.strftime('%Y-%m-%d'))

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '发言统计', '统计分析')

    def get_query(self):
        return get_list_by_botassign(SpeakCount, SpeakCountView, self)

    def get_count_query(self):
        return get_list_count_by_botassign(SpeakCount, SpeakCountView, self)

    def get_action_form(self):
        '''
            定制Action
        :return: 
        '''

        def bot_query_factory():
            from flask_login import current_user
            from common.bot import BotAssign
            return [r.botid for r in BotAssign.find_by_user(current_user.username)]

        def bot_get_pk(obj):
            return obj

        def bot_get_label(obj):
            from common.bot import Bot
            return Bot.find(obj).name

        def target_query_factory():
            from flask_login import current_user
            from plugins.setting import TargetRule
            return [r.botid + '|' + r.target for r in TargetRule.find_allow_by_user(current_user.username)]

        def target_get_pk(obj):
            return obj

        def target_get_label(obj):
            return get_target_display(obj.split('|')[1])

        from wtforms.ext.sqlalchemy.fields import QuerySelectField

        class DoCountForm(self.form_base_class):
            form_widget_args = {}
            form_edit_rules = [
                rules.Field('botid'),
                rules.Field('target'),
                rules.Field('date_from'),
                rules.Field('date_to')
            ]
            _form_edit_rules = rules.RuleSet(self, form_edit_rules)
            action = HiddenField('')
            url = HiddenField('')

            botid = QuerySelectField('机器人', [validators.required(message = '机器人是必填字段')],
                                     query_factory = bot_query_factory, get_label = bot_get_label,
                                     get_pk = bot_get_pk, widget = Select2Widget())

            target = QuerySelectField('目标', [validators.required(message = '目标是必填字段')],
                                      query_factory = target_query_factory, get_label = target_get_label,
                                      get_pk = target_get_pk, widget = Select2Widget())

            date_from = fields.DateField('开始日期', [validators.required(message = '开始日期是必填字段')],
                                         widget = DatePickerWidget())
            date_to = fields.DateField('结束日期', [validators.required(message = '结束日期是必填字段')],
                                       widget = DatePickerWidget())

        return DoCountForm

    @expose('/do/', methods = ('GET', 'POST'))
    def do_view(self):
        """
            Reset password view
        """
        return_url = get_redirect_target() or self.get_url('.index_view')
        # return self.render('model/do.html',return_url = return_url)

        form = self.action_form()

        if validate_form_on_submit(form):
            result = SpeakCount.do(form.data.get('botid'),
                                   target_prefix2name(form.data.get('target').split('|')[1].split('#')[0]),
                                   form.data.get('target').split('|')[1].split('#')[1],
                                   str(form.data.get('date_from')),
                                   str(form.data.get('date_to')))
            # if result:
            return redirect(return_url)

        if not hasattr(form, '_validated_ruleset') or not form._validated_ruleset:
            self._validate_form_instance(ruleset = form._form_edit_rules, form = form)

        if self.validate_form(form):
            pass
            # if self.update_model(form, None):
            #     flash(gettext('Record was successfully saved.'), 'success')
            #     if '_add_another' in request.form:
            #         return redirect(self.get_url('.create_view', url = return_url))
            #     elif '_continue_editing' in request.form:
            #         return redirect(request.url)
            #     else:
            #         # save button
            #         return redirect(self.get_save_return_url(None, is_created = False))

        if request.method == 'GET' or form.errors:
            self.on_form_prefill(form, id)

        form_opts = FormOpts(widget_args = form.form_widget_args,
                             form_rules = form._form_edit_rules)

        template = 'model/do.html'

        return self.render(template,
                           model = None,
                           form = form,
                           form_opts = form_opts,
                           return_url = return_url,
                           brand = request.args.get("caption"))

    @expose('/statistics/', methods = ('GET', 'POST'))
    def get_statistics_data(self):
        def get_speak_statistics(botid, target, date_from, date_to):
            max_count = 0
            min_count = 0
            statistics_data = SpeakCount.statistics(botid,
                                                    target_prefix2name(target.split('#')[0]),
                                                    target.split('#')[1],
                                                    date_from,
                                                    date_to).fetchall()

            for r in statistics_data:
                max_count = max(max_count, int(r.message_count))
                min_count = min(min_count if min_count != 0 else max_count, int(r.vaild_count))

            return {'success': 1,
                               'data': {
                                   'botid': botid,
                                   'target': target,
                                   'statistics_data': [
                                       {'date': r.date, 'message_count': r.message_count,
                                        'vaild_count': r.vaild_count} for r
                                       in statistics_data],
                                   'max_speaks': math.ceil(max_count / 100) * 100,
                                   'mix_speaks': math.floor(min_count / 100) * 100}
                               }

        def do_speak_statistics(botid, target, date_from, date_to):
            if SpeakCount.do(botid,
                             target_prefix2name(target.split('#')[0]),
                             target.split('#')[1],
                             date_from,
                             date_to):
                return {'success': 1}
            else:
                return {'success': 0}

        type = request.form.get('type')
        botid = request.form.get('botid')
        target = request.form.get('target')
        days = request.form.get('days')

        if int(type) == 1:
            if int(days) == 7 or int(days) == 30 or int(days) == 60:
                return json.dumps(get_speak_statistics(botid,
                                            target,
                                            output_datetime(get_now() - timedelta(days = int(days)), True, False),
                                            output_datetime(get_now(), True, False)))
            else:
                return json.dumps({'success': 0})
        elif int(type) == 2:
            return json.dumps(do_speak_statistics(botid,
                                       target, output_datetime(get_now(), True, False),
                                       output_datetime(get_now(), True, False)))
        else:
            return json.dumps({'success': 0})


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
                                  date = output_datetime(record.date),
                                  time = output_datetime(record.time),
                                  create_at = output_datetime(record.create_at),
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
                                  date = output_datetime(record.date),
                                  time = output_datetime(record.time),
                                  create_at = output_datetime(record.create_at),
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
                return ac.success(update_count = result[0],
                                  update_duartion = result[1])
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
class SpeakDailyCountAPI(Resource):
    method_decorators = [ac.require_apikey]

    def get(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('target_type', required = True, help = '请求中必须包含target_type')
            parser.add_argument('target_account', required = True, help = '请求中必须包含target_account')
            parser.add_argument('date_from', required = True, help = '请求中必须包含date_from')
            parser.add_argument('date_to', required = True, help = '请求中必须包含date_to')

            args = parser.parse_args()
            result = SpeakCount.do(ac.get_bot(),
                                   args['target_type'],
                                   args['target_account'],
                                   args['date_from'],
                                   args['date_to'])
            if result:
                return ac.success(target_type = args['target_type'],
                                  target_account = args['target_account'],
                                  date_from = args['date_from'],
                                  date_to = args['date_to'])
            else:
                return ac.fault(error = Exception('未知原因导致数据操作失败'))
        except Exception as e:
            return ac.fault(error = e)


@ac.register_api('/speaktatistics', endpoint = 'speaktatistics')
class SpeakStatisticsAPI(Resource):
    method_decorators = [ac.require_apikey]

    def get(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('target_type', required = True, help = '请求中必须包含target_type')
            parser.add_argument('target_account', required = True, help = '请求中必须包含target_account')
            parser.add_argument('date_from', required = True, help = '请求中必须包含date_from')
            parser.add_argument('date_to', required = True, help = '请求中必须包含date_to')

            args = parser.parse_args()
            records = SpeakCount.statistics(ac.get_bot(),
                                            args['target_type'],
                                            args['target_account'],
                                            args['date_from'],
                                            args['date_to'])
            result = []
            for record in records:
                result.append({'botid': record.botid,
                               'target': record.target,
                               'date': record.date,
                               'message_count': record.message_count,
                               'vaild_count': record.vaild_count})

            if records is not None:
                return ac.success(target_type = args['target_type'],
                                  target_account = args['target_account'],
                                  date_from = args['date_from'],
                                  date_to = args['date_to'],
                                  records = result)
            else:
                return ac.fault(error = Exception('未知原因导致数据操作失败'))
        except Exception as e:
            return ac.fault(error = e)