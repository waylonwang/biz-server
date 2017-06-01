import flask_login as login
from wtforms import validators, fields, StringField

import db_control
from app_view import CVAdminModelView
from common.util import get_now, display_datetime, get_botname, get_yesno_display
from plugin import PluginsRegistry

__registry__ = pr = PluginsRegistry()

db = db_control.get_db()


@pr.register_model(93)
class Bot(db.Model):
    __bind_key__ = 'default'
    __tablename__ = 'bot'

    id = db.Column(db.String(20), primary_key = True)
    name = db.Column(db.String(20), nullable = False)
    active = db.Column(db.Integer, nullable = False, index = True)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    update_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now())
    remark = db.Column(db.String(255), nullable = True)

    @staticmethod
    def findall():
        return Bot.query.all()

    @staticmethod
    def find(botid):
        return Bot.query.get(botid)


@pr.register_model(94)
class BotAssign(db.Model):
    __bind_key__ = 'default'
    __tablename__ = 'bot_assign'

    botid = db.Column(db.String(20), primary_key = True)
    username = db.Column(db.String(255), primary_key = True)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    update_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now())
    remark = db.Column(db.String(255), nullable = True)

    @staticmethod
    def find_by_user(username):
        return BotAssign.query.filter_by(username = username).all()

    @staticmethod
    def find_by_bot(botid):
        return BotAssign.query.filter_by(botid = botid).all()


@pr.register_view()
class BotView(CVAdminModelView):
    can_create = True
    can_edit = True
    can_delete = True

    column_display_pk = True

    column_labels = dict(id = '机器人ID', name = '名称', active = '启用', create_at = '创建时间', update_at = '更新时间',
                         remark = '备注')
    column_formatters = dict(active = lambda v, c, m, p: get_yesno_display(m.active),
                             create_at = lambda v, c, m, p: display_datetime(m.create_at),
                             update_at = lambda v, c, m, p: display_datetime(m.update_at))
    form_edit_rules = ('id', 'name', 'active', 'remark')
    form_create_rules = ('id', 'name', 'active', 'remark')

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '机器人', '系统设置')

    def is_accessible(self):
        from common.login import admin_permission
        if admin_permission.can():
            return login.current_user.is_authenticated
        else:
            return False

    def get_create_form(self):
        form = self.scaffold_form()
        form.id = StringField('机器人ID', [validators.required(message = '机器人ID是必填字段')])
        form.active = fields.BooleanField('启用状态', [validators.required(message = '启用状态是必填字段')])
        return form

    def get_edit_form(self):
        form = self.scaffold_form()
        form.id = StringField('机器人ID', render_kw = {'readonly': True})
        form.active = fields.BooleanField('启用状态', [validators.required(message = '启用状态是必填字段')])
        return form


@pr.register_view()
class BotAssignView(CVAdminModelView):
    can_create = True
    can_edit = True
    can_delete = True

    column_display_pk = True

    column_labels = dict(botid = '机器人', username = '用户名', create_at = '创建时间', update_at = '更新时间', remark = '备注')
    column_formatters = dict(botid = lambda v, c, m, p: get_botname(m.botid),
                             create_at = lambda v, c, m, p: display_datetime(m.create_at),
                             update_at = lambda v, c, m, p: display_datetime(m.update_at))
    form_edit_rules = ('botid', 'botname', 'username', 'remark')
    form_create_rules = ('botid', 'username', 'remark')

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '机器人分派', '系统设置')

    def is_accessible(self):
        from common.login import admin_permission
        if admin_permission.can():
            return login.current_user.is_authenticated
        else:
            return False

    def get_create_form(self):
        form = self.scaffold_form()

        def bot_query_factory():
            return [r.id for r in Bot.findall()]

        def bot_get_pk(obj):
            return obj

        def bot_get_label(obj):
            return Bot.find(obj).name

        from wtforms.ext.sqlalchemy.fields import QuerySelectField
        form.botid = QuerySelectField('机器人', [validators.required(message = '机器人是必填字段')],
                                      query_factory = bot_query_factory, get_label = bot_get_label, get_pk = bot_get_pk)

        from common.user import User
        def user_query_factory():
            return [r.username for r in User.findall()]

        def user_get_pk(obj):
            return obj

        form.username = QuerySelectField('用户名', [validators.required(message = '用户名是必填字段')],
                                         query_factory = user_query_factory, get_pk = user_get_pk)

        return form

    def get_edit_form(self):
        form = self.scaffold_form()
        form.botid = fields.StringField('机器人ID', render_kw = {'readonly': True})
        form.botname = fields.StringField('机器人名称', render_kw = {'readonly': True})
        # form.botname.data = get_botname(form.botid.data)
        form.username = fields.StringField('用户名', render_kw = {'readonly': True})
        return form

    def on_form_prefill(self, form, id):
        form.botname.data = get_botname(id.split(',')[0])


db.create_all()