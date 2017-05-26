from datetime import datetime

from flask_admin.form import rules
from wtforms import validators, fields

import api_control as ac
import db_control
from app_view import CVAdminModelView
from common.util import get_now, display_datetime, get_botname, get_yesno_display, get_acttype_display,\
    get_acttype_choice, get_target_type_choice, get_target_value, get_target_display, get_omit_display
from plugin import PluginsRegistry

__registry__ = cr = PluginsRegistry()

# Model----------------------------------------------------------------------------------------------------
db = db_control.get_db()
api = ac.get_api()


class ScoreAccount(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'score_account'

    botid = db.Column(db.String(20), primary_key = True)
    name = db.Column(db.String(20), primary_key = True, unique = True)
    description = db.Column(db.String(20), nullable = True)
    type = db.Column(db.String(20), nullable = True, index = True)
    is_default = db.Column(db.Integer, nullable = True, index = True)
    target = db.Column(db.String(20), nullable = True)
    income = db.Column(db.Integer, nullable = True)
    outgo = db.Column(db.Integer, nullable = True)
    balance = db.Column(db.Integer, nullable = True)
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


class ScoreMember(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'score_member'

    account = db.Column(db.String(20), primary_key = True)
    member_id = db.Column(db.String(20), primary_key = True)
    member_name = db.Column(db.String(20), nullable = False, index = True)
    income = db.Column(db.Integer, nullable = False)
    outgo = db.Column(db.Integer, nullable = False)
    balance = db.Column(db.Integer, nullable = False)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    update_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now())
    remark = db.Column(db.String(255), nullable = True)


class ScoreRule(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'score_rule'

    account = db.Column(db.String(20), primary_key = True)
    name = db.Column(db.String(20), primary_key = True)
    description = db.Column(db.String(20), nullable = True, index = True)
    type = db.Column(db.String(20), nullable = False, index = True)
    amount = db.Column(db.Integer, nullable = False)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    update_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now())
    remark = db.Column(db.String(255), nullable = True)


class ScoreRecord(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'score_record'

    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    account = db.Column(db.String(20), nullable = False, index = True)
    trans_type = db.Column(db.String(20), nullable = False, index = True)
    outgo_member_id = db.Column(db.String(20), nullable = False, index = True)
    outgo_member_name = db.Column(db.String(20), nullable = False, index = True)
    outgo_amount = db.Column(db.Integer, nullable = False)
    income_member_id = db.Column(db.String(20), nullable = False, index = True)
    income_member_name = db.Column(db.String(20), nullable = False, index = True)
    income_amount = db.Column(db.Integer, nullable = False)
    biz_type = db.Column(db.String(20), nullable = False, index = True)
    date = db.Column(db.Date, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now().date,
                     index = True)
    time = db.Column(db.Time, nullable = False, default = lambda: datetime.time(get_now()),
                     onupdate = lambda: datetime.time(get_now()),
                     index = True)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    remark = db.Column(db.String(255), nullable = True)


db.create_all()


@cr.model('75-ScoreAccount')
def get_ScoreAccount_model():
    return ScoreAccount


@cr.model('76-ScoreRule')
def get_ScoreRule_model():
    return ScoreRule


@cr.model('30-ScoreMember')
def get_ScoreMember_model():
    return ScoreMember


@cr.model('31-ScoreRecord')
def get_ScoreRecord_model():
    return ScoreRecord


# View-----------------------------------------------------------------------------------------------------
class ScoreAccountView(CVAdminModelView):
    can_create = True
    can_edit = True
    can_delete = True
    page_size = 100
    column_filters = ('target', 'type', 'is_default', 'income', 'outgo', 'balance')
    column_list = (
        'botid', 'name', 'description', 'type', 'is_default', 'target', 'income', 'outgo', 'balance', 'create_at',
        'update_at', 'remark')
    column_searchable_list = ('name', 'description', 'remark')
    column_labels = dict(botid = '机器人',
                         name = '账户名',
                         description = '账户描述',
                         type = '账户类型',
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
                             description = lambda v, c, m, p: get_omit_display(m.description),
                             remark = lambda v, c, m, p: get_omit_display(m.remark),
                             create_at = lambda v, c, m, p: display_datetime(m.create_at),
                             update_at = lambda v, c, m, p: display_datetime(m.update_at),
                             type = lambda v, c, m, p: get_acttype_display(m.type),
                             is_default = lambda v, c, m, p: get_yesno_display(m.is_default))
    form_columns = ('botid', 'name', 'description', 'type', 'is_default', 'target', 'remark')
    form_create_rules = (
        rules.FieldSet(('botid', 'name', 'description', 'remark'), '基本信息'),
        rules.FieldSet(('target_type', 'target_account'), '目标设置'),
        rules.FieldSet(('type', 'is_default'), '其他选项')
    )
    form_edit_rules = (
        rules.FieldSet(('botid', 'name', 'description', 'remark'), '基本信息'),
        rules.FieldSet(('target_type', 'target_account'), '目标设置'),
        rules.FieldSet(('type', 'is_default'), '其他选项')
    )

    # form_choices = {'is_default': get_yesno_choice(),
    #                 'type': get_acttype_choice()}

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '积分账户设置', '机器人设置')

    def get_query(self):
        from flask_login import current_user
        if not current_user.is_admin():
            return super(ScoreAccountView, self).get_query().filter(self.model.botid == current_user.username)
        else:
            return super(ScoreAccountView, self).get_query()

    def get_count_query(self):
        from flask_login import current_user
        from flask_admin.contrib.sqla.view import func
        if not current_user.is_admin():
            return self.session.query(func.count('*')).filter(self.model.botid == current_user.username)
        else:
            return super(ScoreAccountView, self).get_count_query()

    def get_create_form(self):
        form = self.scaffold_form()
        delattr(form, 'target')
        form.target_type = fields.SelectField('目标类型', coerce = str, choices = get_target_type_choice())
        form.target_account = fields.StringField('目标账号', [validators.required(message = '目标账号是必填字段')])
        form.type = fields.SelectField('类型', coerce = str, choices = get_acttype_choice())
        form.is_default = fields.BooleanField('缺省账户')

        def query_factory():
            from flask_login import current_user
            from common.bot import BotAssign
            return [r.botid for r in BotAssign.find_by_user(current_user.username)]

        def get_pk(obj):
            return obj

        def get_label(obj):
            from common.bot import Bot
            return Bot.find(obj).name

        from wtforms.ext.sqlalchemy.fields import QuerySelectField
        form.botid = QuerySelectField('机器人', [validators.required(message = '机器人是必填字段')],
                                      query_factory = query_factory, get_label = get_label, get_pk = get_pk)
        return form

    def get_edit_form(self):
        form = self.scaffold_form()
        # delattr(form, 'target')
        form.target_type = fields.SelectField('目标类型', [validators.required(message = '目标类型是必填字段')],
                                              coerce = str,
                                              choices = get_target_type_choice())
        form.target_account = fields.StringField('目标账号', [validators.required(message = '目标账号是必填字段')])
        form.botid = fields.StringField('机器人ID', render_kw = {'readonly': True})
        form.type = fields.SelectField('类型', coerce = str, choices = get_acttype_choice())
        form.is_default = fields.BooleanField('缺省账户')

        def query_factory():
            return self.model.find_by_id()

        return form

    def on_model_change(self, form, model, is_created):
        model.target = get_target_value(form.target_type.data, form.target_account.data)

    def on_form_prefill(self, form, id):
        target = self.model.find_by_id(id).target
        form.target_account.data = target.replace(target[0:2], '')


class ScoreMemberView(CVAdminModelView):
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 100
    column_filters = ('account', 'member_id', 'member_name', 'income', 'outgo', 'balance')
    column_list = (
        'account', 'member_id', 'member_name', 'income', 'outgo', 'balance')
    column_searchable_list = ('member_name', 'remark')
    column_labels = dict(account = '账户名',
                         member_id = '成员账号',
                         member_name = '成员名称',
                         income = '总收入',
                         outgo = '总支出',
                         balance = '余额',
                         create_at = '创建时间',
                         remark = '备注')
    column_formatters = dict(member_name = lambda v, c, m, p: get_omit_display(m.member_name),
                             remark = lambda v, c, m, p: get_omit_display(m.remark))

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '成员积分', '积分管理')


class ScoreRuleView(CVAdminModelView):
    can_create = True
    can_edit = True
    can_delete = True
    column_filters = ('account', 'name', 'type')
    column_list = (
        'account', 'name', 'description', 'type', 'amount', 'create_at', 'update_at', 'remark')
    column_searchable_list = ('description', 'remark')
    column_labels = dict(account = '账户名',
                         name = '规则名',
                         description = '描述',
                         type = '类型',
                         amount = '数量',
                         create_at = '创建时间',
                         update_at = '更新时间',
                         remark = '备注')
    column_formatters = dict(description = lambda v, c, m, p: get_omit_display(m.description),
                             remark = lambda v, c, m, p: get_omit_display(m.remark),
                             create_at = lambda v, c, m, p: display_datetime(m.create_at),
                             update_at = lambda v, c, m, p: display_datetime(m.update_at),
                             type = lambda v, c, m, p: get_acttype_display(m.type))
    form_columns = ('account', 'name', 'description', 'type', 'amount', 'remark')

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '积分规则设置', '机器人设置')

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
                                        query_factory = query_factory, get_label = get_label, get_pk = get_pk)
        form.name = fields.StringField('规则名', [validators.required(message = '规则名是必填字段')])
        form.description = fields.StringField('描述')
        form.type = fields.SelectField('类型', coerce = str, choices = get_acttype_choice())
        form.amount = fields.StringField('数量', [validators.required(message = '数量是必填字段')])
        form.remark = fields.StringField('备注')
        return form

    def get_edit_form(self):
        form = self.scaffold_form()
        form.account = fields.StringField('账户名', render_kw = {'readonly': True})
        form.name = fields.StringField('规则名', render_kw = {'readonly': True})
        form.type = fields.SelectField('类型', coerce = str, choices = get_acttype_choice())
        form.description = fields.StringField('描述')
        form.type = fields.SelectField('类型', coerce = str, choices = get_acttype_choice())
        form.amount = fields.StringField('数量', [validators.required(message = '数量是必填字段')])
        form.remark = fields.StringField('备注')
        return form


# todo 优化类型等显示
# todo member考虑改为一个字段
class ScoreRecordView(CVAdminModelView):
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 100
    column_filters = ('account', 'trans_type',
                      'outgo_member_id', 'income_member_id',
                      'outgo_amount', 'income_amount',
                      'biz_type', 'date')
    column_list = (
        'account', 'trans_type',
        'outgo_member_id', 'outgo_member_name', 'outgo_amount',
        'income_member_id', 'income_member_name', 'income_amount',
        'biz_type', 'date', 'time', 'remark')
    column_searchable_list = ('outgo_member_name', 'income_member_name', 'remark')
    column_labels = dict(account = '账户名',
                         trans_type = '交易类型',
                         outgo_member_id = '转出成员账号',
                         outgo_member_name = '转出成员名称',
                         outgo_amount = '转出数量',
                         income_member_id = '转入成员账号',
                         income_member_name = '转入成员名称',
                         income_amount = '转入数量',
                         biz_type = '来源类型',
                         date = '日期',
                         time = '时间',
                         remark = '消息')
    column_formatters = dict(target = lambda v, c, m, p: get_target_display(m.target),
                             outgo_member_name = lambda v, c, m, p: get_omit_display(m.outgo_member_name),
                             income_member_name = lambda v, c, m, p: get_omit_display(m.income_member_name),
                             remark = lambda v, c, m, p: get_omit_display(m.remark))

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '积分记录', '积分管理')


@cr.view('75-ScoreAccount')
def get_ScoreAccount_view():
    return ScoreAccountView


@cr.view('76-ScoreRule')
def get_ScoreRule_view():
    return ScoreRuleView


@cr.view('30-ScoreMember')
def get_ScoreMember_view():
    return ScoreMemberView


@cr.view('31-ScoreRecord')
def get_ScoreRecord_view():
    return ScoreRecordView