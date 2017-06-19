import uuid
from datetime import datetime

from flask import url_for
from flask_admin.form import rules, Select2Widget
from flask_restful import Resource, reqparse
from markupsafe import Markup
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker
from wtforms import validators, fields

import api_control as ac
import db_control
from app_view import CVAdminModelView
from common.bot import Bot
from common.util import get_now, display_datetime, get_botname, get_yesno_display, get_acttype_display,\
    get_acttype_choice, get_target_display, output_datetime,\
    get_transtype_display, get_list_by_botassign, get_list_count_by_botassign, get_list_by_scoreaccount,\
    get_list_count_by_scoreaccount, recover_target_value, get_CQ_display, get_target_composevalue
from plugin import PluginsRegistry

__registry__ = pr = PluginsRegistry()

# Model----------------------------------------------------------------------------------------------------
db = db_control.get_db()


@pr.register_model(75)
class ScoreAccount(db.Model):
    """
    积分账户说明：
    1.每个机器人可以拥有多个积分账户，这些积分账户可以分布在同一个目标中，也可以分布在不同目标中
    2.无论归属哪个机器人，所有积分账户的账户名不能重复
    3.在未指定账户时，积分记账记入机器人的缺省账户
    """
    __bind_key__ = 'score'
    __tablename__ = 'score_account'

    botid = db.Column(db.String(20), primary_key = True)
    name = db.Column(db.String(20), primary_key = True, unique = True)
    description = db.Column(db.String(20), nullable = True)
    # type = db.Column(db.String(20), nullable = True, index = True)
    is_default = db.Column(db.Integer, nullable = True, index = True)
    target = db.Column(db.String(20), nullable = True)
    income = db.Column(db.Integer, nullable = True, default = 0)
    outgo = db.Column(db.Integer, nullable = True, default = 0)
    balance = db.Column(db.Integer, nullable = True, default = 0)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    update_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now())
    remark = db.Column(db.String(255), nullable = True)

    @staticmethod
    def find_by_user(username):
        from common.bot import BotAssign
        return ScoreAccount.query.filter(
            ScoreAccount.botid.in_((r.botid for r in BotAssign.find_by_user(username)))).all()

    @staticmethod
    def find_by_id(id):
        return ScoreAccount.query.filter_by(botid = id.split(',')[0], name = id.split(',')[1]).first()

    @staticmethod
    def find_by_target(botid, target_type, target_account):
        target = get_target_composevalue(target_type, target_account)
        return ScoreAccount.query.filter_by(botid = botid, target = target).all()

    @staticmethod
    def get_acount(name):
        return ScoreAccount.query.filter_by(name = name).first()

    @staticmethod
    def increase(account: str, member_id: str, amount: int):
        act = ScoreAccount.get_acount(account)
        if act is None: return None
        act.income += amount
        act.balance += amount
        ScoreAccount.query.session.commit()

    @staticmethod
    def reduce(account: str, member_id: str, amount: int):
        act = ScoreAccount.get_acount(account)
        if act is None: return None
        act.outgo += amount
        act.balance -= amount
        ScoreAccount.query.session.commit()

    @staticmethod
    def get_default(botid):
        return ScoreAccount.query.filter_by(botid = botid, is_default = True).first()


@pr.register_model(76)
class ScoreRule(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'score_rule'

    account = db.Column(db.String(20), primary_key = True)
    code = db.Column(db.String(20), primary_key = True)
    description = db.Column(db.String(20), nullable = True, index = True)
    type = db.Column(db.String(20), nullable = False, index = True)
    amount = db.Column(db.Integer, nullable = True, default = 0)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    update_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now())
    remark = db.Column(db.String(255), nullable = True)

    @staticmethod
    def get_rule(account, code):
        return ScoreRule.query.filter_by(account = account, code = code).first()


@pr.register_model(30)
class ScoreMember(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'score_member'

    account = db.Column(db.String(20), primary_key = True)
    member_id = db.Column(db.String(20), primary_key = True)
    member_name = db.Column(db.String(20), nullable = True)
    income = db.Column(db.Integer, nullable = False, default = 0)
    outgo = db.Column(db.Integer, nullable = False, default = 0)
    balance = db.Column(db.Integer, nullable = False, default = 0)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    update_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now())
    remark = db.Column(db.String(255), nullable = True)

    @staticmethod
    def get_member(account, member_id, **kwargs):
        member = ScoreMember.query.filter_by(account = account, member_id = member_id)
        if member.first() is None:
            member = ScoreMember(account = account,
                                 member_id = member_id,
                                 income = 0,
                                 outgo = 0,
                                 balance = 0,
                                 member_name = '' if kwargs.get('member_name') is None else kwargs.get(
                                     'member_name'),
                                 remark = '' if kwargs.get('remark') is None else kwargs.get('remark'))
            ScoreMember.query.session.add(member)
            ScoreMember.query.session.commit()
            return member
        else:
            return member.first()

    @staticmethod
    def increase(account: str, member_id: str, amount: int, **kwargs):
        member = ScoreMember.get_member(account, member_id, **kwargs)
        member.income += amount
        member.balance += amount
        ScoreMember.query.session.commit()

    @staticmethod
    def reduce(account: str, member_id: str, amount: int, **kwargs):
        member = ScoreMember.get_member(account, member_id, **kwargs)
        member.outgo += amount
        member.balance -= amount
        ScoreMember.query.session.commit()


@pr.register_model(31)
class ScoreRecord(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'score_record'

    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    account = db.Column(db.String(20), nullable = False, index = True)
    biz_type = db.Column(db.String(20), nullable = False, index = True)
    trans_type = db.Column(db.String(20), nullable = False, index = True)
    transfer_id = db.Column(db.String(32), nullable = True)
    member_id = db.Column(db.String(20), nullable = True, index = True)
    member_name = db.Column(db.String(20), nullable = True, index = True)
    amount = db.Column(db.Integer, nullable = True, default = 0)
    before = db.Column(db.Integer, nullable = True, default = 0)
    after = db.Column(db.Integer, nullable = True, default = 0)
    date = db.Column(db.Date, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now().date,
                     index = True)
    time = db.Column(db.Time, nullable = False, default = lambda: datetime.time(get_now()),
                     onupdate = lambda: datetime.time(get_now()),
                     index = True)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    remark = db.Column(db.String(255), nullable = True)

    @staticmethod
    def create_change(biz_type: str, member_id: str, amount: int = None, account: str = None, **kwargs):
        if account is None:
            act = ScoreAccount.get_default(kwargs.get('botid'))
            if act is not None:
                account = act.name
        if account is None: return None

        rule = ScoreRule.get_rule(account, biz_type)
        if rule is None or not (rule.type == 'income' or rule.type == 'outgo'): return None

        amount = amount if amount is not None else rule.amount

        before = ScoreMember.get_member(account, member_id,
                                        member_name = kwargs.get('member_name', member_id),
                                        remark = '积分变更自动创建').balance
        after = before + amount if rule.type == 'income' else before - amount
        record = ScoreRecord(account = account,
                             biz_type = biz_type,
                             trans_type = rule.type,
                             member_id = member_id,
                             amount = amount,
                             before = before,
                             after = after,
                             member_name = '' if kwargs.get('member_name') is None else kwargs.get(
                                 'member_name'),
                             remark = '' if kwargs.get('remark') is None else kwargs.get('remark'))

        record.query.session.add(record)
        record.query.session.commit()

        if rule.type == 'outgo':
            ScoreMember.reduce(account, member_id, amount, **kwargs)
            ScoreAccount.reduce(account, member_id, amount)
        else:
            ScoreMember.increase(account, member_id, amount, **kwargs)
            ScoreAccount.increase(account, member_id, amount)
        return record

    @staticmethod
    def create_transfer(biz_type: str, outgo_member_id: str, income_member_id: str, amount: int, account: str = None,
                        **kwargs):
        if account is None:
            act = ScoreAccount.get_default(kwargs.get('botid'))
            if act is not None:
                account = act.name
        if account is None: return None

        rule = ScoreRule.get_rule(account, biz_type)
        if rule is None or rule.type != 'transfer': return None

        transfer_id = uuid.uuid1().hex

        before = ScoreMember.get_member(account, outgo_member_id,
                                        member_name = kwargs.get('outgo_member_name', outgo_member_id),
                                        remark = '积分转账自动创建').balance
        record = ScoreRecord(account = account,
                             biz_type = biz_type,
                             trans_type = rule.type,
                             transfer_id = transfer_id,
                             member_id = outgo_member_id,
                             amount = amount * -1,
                             before = before,
                             after = before - amount,
                             member_name = '' if kwargs.get('outgo_member_name') is None else kwargs.get(
                                 'outgo_member_name'),
                             remark = '' if kwargs.get('remark') is None else kwargs.get('remark'))
        record.query.session.add(record)

        before = ScoreMember.get_member(account, income_member_id,
                                        member_name = kwargs.get('income_member_name', income_member_id),
                                        remark = '积分转账自动创建').balance
        record = ScoreRecord(account = account,
                             biz_type = biz_type,
                             trans_type = rule.type,
                             transfer_id = transfer_id,
                             member_id = income_member_id,
                             amount = amount,
                             before = before,
                             after = before + amount,
                             member_name = '' if kwargs.get('income_member_name') is None else kwargs.get(
                                 'income_member_name'),
                             remark = '' if kwargs.get('remark') is None else kwargs.get('remark'))
        record.query.session.add(record)
        record.query.session.commit()

        ScoreMember.reduce(account, outgo_member_id, amount, **kwargs)
        ScoreAccount.reduce(account, outgo_member_id, amount)
        ScoreMember.increase(account, income_member_id, amount, **kwargs)
        ScoreAccount.increase(account, income_member_id, amount)

        return record

    @staticmethod
    def find_by_member(member_id):
        session = sessionmaker(bind = db.get_engine(bind = 'score'))()
        cnts = session.execute('SELECT count(1) cnt FROM score_record WHERE member_id = :id', {'id': member_id})
        if cnts is not None:
            return cnts.first()
        return None

    @staticmethod
    def find_first_by_member_name(member_name):
        return ScoreRecord.query.filter_by(member_name = member_name).first()

    @staticmethod
    def get_flow(botid, target_type, target_account, date_from, date_to, member = None):
        if member is None:
            member_id = None
        elif not member.isdigit():
            record = ScoreRecord.find_first_by_member_name(member)
            member_id = record.member_id
        else:
            member_id = member

        accounts = ScoreAccount.find_by_target(botid, target_type, target_account)

        return ScoreRecord.query.session.query(
            func.sum(func.abs(ScoreRecord.amount)).label('total')
        ).filter(
            ScoreRecord.account.in_((r.name for r in accounts)) if len(accounts) > 0 else 1 == 1,
            ScoreRecord.date >= date_from,
            ScoreRecord.date <= date_to,
            ScoreRecord.member_id == member_id if member_id is not None else 1 == 1
        ).first()


db.create_all()


# View-----------------------------------------------------------------------------------------------------
@pr.register_view()
class ScoreAccountView(CVAdminModelView):
    can_create = True
    can_edit = True
    can_delete = True
    page_size = 100
    column_filters = ('target',
                      # 'type',
                      'is_default', 'income', 'outgo', 'balance')
    column_list = (
        'botid', 'name', 'description',
        # 'type',
        'is_default', 'target', 'income', 'outgo', 'balance', 'create_at',
        'update_at', 'remark')
    column_searchable_list = ('name', 'description', 'remark')
    column_labels = dict(botid = '机器人',
                         name = '账户名',
                         description = '账户描述',
                         # type = '账户类型',
                         is_default = '缺省账户',
                         target = '目标',
                         income = '总收入',
                         outgo = '总支出',
                         balance = '余额',
                         create_at = '创建时间',
                         update_at = '更新时间',
                         remark = '备注')
    column_formatters = dict(botid = lambda v, c, m, p: get_botname(m.botid),
                             target = lambda v, c, m, p: get_target_display(m.target),
                             create_at = lambda v, c, m, p: display_datetime(m.create_at),
                             update_at = lambda v, c, m, p: display_datetime(m.update_at),
                             # type = lambda v, c, m, p: get_acttype_display(m.type),
                             is_default = lambda v, c, m, p: get_yesno_display(m.is_default))
    form_columns = ('botid', 'name', 'description',
                    # 'type',
                    'is_default', 'target', 'remark')
    form_create_rules = (
        rules.FieldSet(('botid', 'target'), '目标设置'),
        rules.FieldSet(('name', 'description', 'remark'), '基本信息'),
        rules.FieldSet((
            # 'type',
            'is_default',), '其他选项')
    )
    form_edit_rules = (
        rules.FieldSet(('botid', 'target'), '目标设置'),
        rules.FieldSet(('name', 'description', 'remark'), '基本信息'),
        rules.FieldSet((
            # 'type',
            'is_default',), '其他选项')
    )

    # form_choices = {'is_default': get_yesno_choice(),
    #                 'type': get_acttype_choice()}

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '积分账户设置', '机器人设置')

    def get_query(self):
        return get_list_by_botassign(ScoreAccount, ScoreAccountView, self)

    def get_count_query(self):
        return get_list_count_by_botassign(ScoreAccount, ScoreAccountView, self)

    def get_create_form(self):
        form = self.scaffold_form()
        # delattr(form, 'target')
        # form.target_type = fields.SelectField('目标类型', coerce = str, choices = get_target_type_choice())
        # form.target_account = fields.StringField('目标账号', [validators.required(message = '目标账号是必填字段')])
        form.type = fields.SelectField('类型', coerce = str, choices = get_acttype_choice(), widget = Select2Widget())
        form.is_default = fields.BooleanField('缺省账户')

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

        def target_query_factory():
            from flask_login import current_user
            from plugins.setting import TargetRule
            return [r.botid + '|' + r.target for r in TargetRule.find_allow_by_user(current_user.username)]

        def target_get_pk(obj):
            return obj

        def target_get_label(obj):
            return get_target_display(obj.split('|')[1])

        from wtforms.ext.sqlalchemy.fields import QuerySelectField
        form.target = QuerySelectField('目标', [validators.required(message = '目标是必填字段')],
                                       query_factory = target_query_factory, get_label = target_get_label,
                                       get_pk = target_get_pk, widget = Select2Widget())
        return form

    def get_edit_form(self):
        form = self.scaffold_form()
        form.botid = fields.StringField('机器人', render_kw = {'readonly': True})
        form.target = fields.StringField('目标', render_kw = {'readonly': True})
        form.name = fields.StringField('账户名', render_kw = {'readonly': True})
        form.type = fields.SelectField('类型', coerce = str, choices = get_acttype_choice(), widget = Select2Widget())
        form.is_default = fields.BooleanField('缺省账户')

        return form

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.target = form.target.data.split('|')[1]
        else:
            model.botid = Bot.find_by_name(model.botid).id
            model.target = recover_target_value(model.target)

    def on_form_prefill(self, form, id):
        form.botid.data = Bot.find(form.botid.data).name
        form.target.data = get_target_display(form.target.data)


@pr.register_view()
class ScoreMemberView(CVAdminModelView):
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 100
    column_filters = ('account', 'member_id', 'member_name', 'income', 'outgo', 'balance')
    column_list = (
        'account', 'member', 'income', 'outgo', 'balance', 'record_count', 'create_at', 'update_at', 'remark')
    column_searchable_list = ('member_name', 'remark')
    column_labels = dict(account = '账户名',
                         member = '成员',
                         member_id = '成员账号',
                         member_name = '成员名称',
                         income = '总收入',
                         outgo = '总支出',
                         balance = '余额',
                         record_count = '交易次数',
                         create_at = '创建时间',
                         update_at = '更新时间',
                         remark = '备注')

    def _record_formatter(view, context, model, name):
        cnt = ScoreRecord.find_by_member(model.member_id)
        if cnt is not None:
            return Markup(
                u"<a href= '%s'>%s</a>" % (
                    url_for('scorerecord.index_view', flt2_16 = model.member_id),
                    cnt[0]
                )
            )
        else:
            return 0

    column_formatters = dict(member = lambda v, c, m, p: get_CQ_display(m.member_id + ' : ' + m.member_name),
                             record_count = _record_formatter,
                             create_at = lambda v, c, m, p: display_datetime(m.create_at),
                             update_at = lambda v, c, m, p: display_datetime(m.update_at))

    column_default_sort = ('update_at', True)

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '成员积分', '积分管理')

    def get_query(self):
        return get_list_by_scoreaccount(ScoreMember, ScoreMemberView, self)

    def get_count_query(self):
        return get_list_count_by_scoreaccount(ScoreMember, ScoreMemberView, self)


@pr.register_view()
class ScoreRuleView(CVAdminModelView):
    can_create = True
    can_edit = True
    can_delete = True
    column_filters = ('account', 'code', 'type')
    column_list = (
        'account', 'code', 'description', 'type', 'amount', 'create_at', 'update_at', 'remark')
    column_searchable_list = ('description', 'remark')
    column_labels = dict(account = '账户名',
                         code = '规则码',
                         description = '描述',
                         type = '类型',
                         amount = '数量',
                         create_at = '创建时间',
                         update_at = '更新时间',
                         remark = '备注')
    column_formatters = dict(create_at = lambda v, c, m, p: display_datetime(m.create_at),
                             update_at = lambda v, c, m, p: display_datetime(m.update_at),
                             type = lambda v, c, m, p: get_acttype_display(m.type))
    form_columns = ('account', 'code', 'description', 'type', 'amount', 'remark')

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '积分规则设置', '机器人设置')

    def get_query(self):
        return get_list_by_scoreaccount(ScoreRule, ScoreRuleView, self)

    def get_count_query(self):
        return get_list_count_by_scoreaccount(ScoreRule, ScoreRuleView, self)

    def get_create_form(self):
        form = self.scaffold_form()

        def query_factory():
            from flask_login import current_user
            return [r.name for r in ScoreAccount.find_by_user(current_user.username)]

        def get_pk(obj):
            return obj

        def get_label(obj):
            return obj

        from wtforms.ext.sqlalchemy.fields import QuerySelectField
        form.account = QuerySelectField('账户名', [validators.required(message = '账户名是必填字段')],
                                        query_factory = query_factory, get_label = get_label, get_pk = get_pk,
                                        widget = Select2Widget())
        form.code = fields.StringField('规则码', [validators.required(message = '规则码是必填字段')])
        form.description = fields.StringField('描述')
        form.type = fields.SelectField('类型', coerce = str, choices = get_acttype_choice(), widget = Select2Widget())
        form.amount = fields.StringField('数量', [validators.required(message = '数量是必填字段')])
        form.remark = fields.StringField('备注')
        return form

    def get_edit_form(self):
        form = self.scaffold_form()
        form.account = fields.StringField('账户名', render_kw = {'readonly': True})
        form.code = fields.StringField('规则码', render_kw = {'readonly': True})
        form.type = fields.SelectField('类型', coerce = str, choices = get_acttype_choice(), widget = Select2Widget())
        form.description = fields.StringField('描述')
        form.type = fields.SelectField('类型', coerce = str, choices = get_acttype_choice(), widget = Select2Widget())
        form.amount = fields.StringField('数量', [validators.required(message = '数量是必填字段')])
        form.remark = fields.StringField('备注')
        return form


@pr.register_view()
class ScoreRecordView(CVAdminModelView):
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 100
    column_filters = ('account', 'trans_type',
                      'member_id', 'amount',
                      'biz_type', 'date')
    column_list = (
        'account', 'biz_type', 'trans_type',
        'member', 'before', 'amount', 'after',
        'date', 'time', 'remark')
    column_searchable_list = ('member_name', 'remark')
    column_labels = dict(account = '账户名',
                         biz_type = '来源类型',
                         trans_type = '交易类型',
                         member = '成员',
                         member_id = '成员账号',
                         member_name = '成员名称',
                         amount = '交易数量',
                         before = '交易前余额',
                         after = '交易后余额',
                         date = '日期',
                         time = '时间',
                         remark = '备注')

    column_formatters = dict(target = lambda v, c, m, p: get_target_display(m.target),
                             biz_type = lambda v, c, m, p: ScoreRule.get_rule(m.account, m.biz_type).description,
                             trans_type = lambda v, c, m, p: get_transtype_display(m.trans_type, m.amount < 0),
                             member = lambda v, c, m, p: get_CQ_display(m.member_id + ' : ' + m.member_name),
                             amount = lambda v, c, m, p: abs(m.amount),
                             date = lambda v, c, m, p: display_datetime(m.create_at, False),
                             time = lambda v, c, m, p: m.time.strftime('%H:%M'))

    column_default_sort = ('id', True)

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '积分记录', '积分管理')

    def get_query(self):
        return get_list_by_scoreaccount(ScoreRecord, ScoreRecordView, self)

    def get_count_query(self):
        return get_list_count_by_scoreaccount(ScoreRecord, ScoreRecordView, self)


# Control--------------------------------------------------------------------------------------------------
@ac.register_api('/score_change', endpoint = 'score_change')
class ScoreChangeAPI(Resource):
    method_decorators = [ac.require_apikey]

    def post(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('biz_type', required = True, help = '请求中必须包含biz_type')
            parser.add_argument('member_id', required = True, help = '请求中必须包含member_id')
            parser.add_argument('amount', type = int)
            parser.add_argument('account')
            parser.add_argument('member_name')
            parser.add_argument('remark')
            args = parser.parse_args()

            record = ScoreRecord.create_change(args['biz_type'],
                                               args['member_id'],
                                               args['amount'],
                                               args['account'],
                                               member_name = args['member_name'],
                                               remark = args['remark'],
                                               botid = ac.get_bot())
            if record is not None:
                return ac.success(account = record.account,
                                  trans_type = record.trans_type,
                                  biz_type = record.biz_type,
                                  member_id = record.member_id,
                                  member_name = record.member_name,
                                  amount = record.amount,
                                  date = output_datetime(record.date),
                                  time = output_datetime(record.time),
                                  create_at = output_datetime(record.create_at),
                                  remark = record.remark)
            else:
                return ac.fault(error = Exception('未知原因导致数据创建失败'))
        except Exception as e:
            return ac.fault(error = e)


@ac.register_api('/score_transfer', endpoint = 'score_transfer')
class ScoreTransferAPI(Resource):
    method_decorators = [ac.require_apikey]

    def post(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('biz_type', required = True, help = '请求中必须包含biz_type')
            parser.add_argument('outgo_member_id', required = True, help = '请求中必须包含outgo_member_id')
            parser.add_argument('income_member_id', required = True, help = '请求中必须包含income_member_id')
            parser.add_argument('amount', type = int, required = True, help = '请求中必须包含amount')
            parser.add_argument('account')
            parser.add_argument('outgo_member_name')
            parser.add_argument('income_member_name')
            parser.add_argument('remark')
            args = parser.parse_args()
            if args['amount'] <= 0:
                return ac.fault(error = Exception('amount必须大于0'))

            record = ScoreRecord.create_transfer(args['biz_type'],
                                                 args['outgo_member_id'],
                                                 args['income_member_id'],
                                                 args['amount'],
                                                 args['account'],
                                                 outgo_member_name = args['outgo_member_name'],
                                                 income_member_name = args['income_member_name'],
                                                 remark = args['remark'],
                                                 botid = ac.get_bot())
            if record is not None:
                return ac.success(account = record.account,
                                  biz_type = record.biz_type,
                                  trans_type = record.trans_type,
                                  outgo_member_id = args['outgo_member_id'],
                                  outgo_member_name = args['outgo_member_name'],
                                  income_member_id = args['income_member_id'],
                                  income_member_name = args['income_member_name'],
                                  amount = record.amount,
                                  date = output_datetime(record.date),
                                  time = output_datetime(record.time),
                                  create_at = output_datetime(record.create_at),
                                  remark = args['remark'])
            else:
                return ac.fault(error = Exception('未知原因导致数据创建失败'))
        except Exception as e:
            return ac.fault(error = e)