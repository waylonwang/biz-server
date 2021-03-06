import flask_login as login
from flask_admin.form import Select2Widget
from wtforms import validators, fields, StringField

import db_control
from app_view import CVAdminModelView
from common.util import get_now, display_datetime, get_botname, get_yesno_display
from plugin import PluginsRegistry

__registry__ = pr = PluginsRegistry()

db = db_control.get_db()


@pr.register_model(94)
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

    @staticmethod
    def find_by_name(name):
        return Bot.query.filter_by(name = name).first()

    @staticmethod
    def destroy(botid):
        from common.apikey import APIKey
        return BotAssign.destroy(botid) and APIKey.destroy(botid)


class BotRegistry():
    def __init__(self):
        self.init_map = {}
        self.destroy_map = {}

    def register_init(self):
        def decorator(func):
            self.init_map[func.__qualname__] = func
            return func

        return decorator

    def register_destroy(self):
        def decorator(func):
            self.destroy_map[func.__qualname__] = func
            return func

        return decorator


bothub = BotRegistry()


def bot_registry():
    # global bothub
    return bothub


@pr.register_model(95)
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

    @staticmethod
    def delete(botid):
        BotAssign.query.filter_by(botid = botid).delete()
        BotAssign.query.session.commit()
        return True

    @staticmethod
    def init_relation(botid):
        '''
        初始化已分配机器人关联的业务数据
        :param botid: 机器人id
        :return: 是否成功
        '''
        for (func_k, func_v) in bothub.init_map.items():
            func_v(botid)
        return True

    @staticmethod
    def destroy_relation(botid):
        '''
        销毁已分配机器人关联的业务数据
        :param botid: 机器人id
        :return: 是否成功
        '''
        for (func_k, func_v) in bothub.destroy_map.items():
            func_v(botid)
        return True

    @staticmethod
    def destroy(botid):
        '''
        销毁已分配的机器人
        :param botid: 机器人id
        :return: 是否成功
        '''
        BotAssign.delete(botid)
        BotAssign.destroy_relation(botid)
        return True


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
        form.active = fields.BooleanField('启用状态', [validators.required(message = '启用状态是必填字段')], default = True)
        return form

    def get_edit_form(self):
        form = self.scaffold_form()
        form.id = StringField('机器人ID', render_kw = {'readonly': True})
        form.active = fields.BooleanField('启用状态', [validators.required(message = '启用状态是必填字段')], default = True)
        return form

    def after_model_delete(self, model):
        Bot.destroy(model.id)


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
                                      query_factory = bot_query_factory, get_label = bot_get_label, get_pk = bot_get_pk,
                                      widget = Select2Widget())

        from common.user import User
        def user_query_factory():
            return [r.username for r in User.findall()]

        def user_get_pk(obj):
            return obj

        form.username = QuerySelectField('用户名', [validators.required(message = '用户名是必填字段')],
                                         query_factory = user_query_factory, get_pk = user_get_pk,
                                         widget = Select2Widget())

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

    def after_model_change(self, form, model, is_created):
        BotAssign.init_relation(model.botid)

    def after_model_delete(self, model):
        BotAssign.destroy(model.botid)


db.create_all()