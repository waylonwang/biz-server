import flask_login as login
from flask import request
from flask_admin import expose
from flask_admin.form import Select2Widget
from flask_admin.helpers import get_redirect_target
from flask_admin.model.helpers import get_mdict_item_or_list
from flask_admin.model.template import EndpointLinkRowAction
from werkzeug.utils import redirect
from wtforms import validators, StringField

import db_control
from app_view import CVAdminModelView
from common.bot import Bot
from common.util import get_now, display_datetime, generate_key, get_botname
from plugin import PluginsRegistry

__registry__ = pr = PluginsRegistry()

db = db_control.get_db()


@pr.register_model(96)
class APIKey(db.Model):
    __bind_key__ = 'default'
    __tablename__ = 'apikey'
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    botid = db.Column(db.String(20), nullable = False, unique = True)
    key = db.Column(db.String(255), nullable = False, unique = True,
                    default = lambda: generate_key(32, True, False, True))
    secret = db.Column(db.String(255), nullable = False, default = lambda: generate_key(12, False, True, True))
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    update_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now())

    @staticmethod
    def find_by_key(key):
        return APIKey.query.filter_by(key = key).first()

    @staticmethod
    def find_by_bot(botid):
        return APIKey.query.filter_by(bitid = botid).first()

    @staticmethod
    def destroy(botid):
        '''
        销毁机器人的API Key
        :param botid: 机器人id
        :return: 是否成功
        '''
        APIKey.query.filter_by(botid = botid).delete()
        APIKey.query.session.commit()
        return True

    def refresh(self):
        self.key = generate_key(32, True, False, True)
        self.secret = generate_key(12, False, True, True)
        self.query.session.commit()


@pr.register_view()
class APIKeyView(CVAdminModelView):
    can_create = True
    can_edit = False
    can_delete = True

    column_labels = dict(id = 'ID', botid = '机器人', key = 'API Key', secret = 'API Secret',
                         create_at = '创建时间', update_at = '更新时间')
    column_formatters = dict(botid = lambda v, c, m, p: get_botname(m.botid),
                             create_at = lambda v, c, m, p: display_datetime(m.create_at),
                             update_at = lambda v, c, m, p: display_datetime(m.update_at))

    column_extra_row_actions = [
        EndpointLinkRowAction('fa fa-refresh', 'apikey.refresh_view', title = '更新Key和Secret')
    ]

    form_create_rules = (
        'botid',
    )

    form_edit_rules = (
        'botid', 'new_key', 'new_secret'
    )

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, 'API密钥', '系统设置')

    def is_accessible(self):
        from common.login import admin_permission
        if admin_permission.can():
            return login.current_user.is_authenticated
        else:
            return False

    def get_create_form(self):
        form = self.scaffold_form()

        def query_factory():
            return [r.id for r in Bot.findall()]

        def get_pk(obj):
            return obj

        def get_label(obj):
            return Bot.find(obj).name

        from wtforms.ext.sqlalchemy.fields import QuerySelectField
        form.botid = QuerySelectField('机器人', [validators.required(message = '机器人是必填字段')],
                                      query_factory = query_factory, get_label = get_label, get_pk = get_pk,
                                      widget = Select2Widget())
        return form

    def get_edit_form(self):
        form = self.scaffold_form()
        delattr(form, 'key')
        delattr(form, 'secret')
        form.botid = StringField('机器人', render_kw = {'readonly': True})
        form.new_key = StringField('新API Key', render_kw = {'readonly': True})
        form.new_secret = StringField('新API Secret', render_kw = {'readonly': True})
        return form

    def on_form_prefill(self, form, id):
        form.new_key.data = generate_key(32, True, False, True)
        form.new_secret.data = generate_key(12, False, True, True)

    def on_model_change(self, form, model, is_created):
        if not is_created:
            if form.new_key.data:
                model.key = form.new_key.data
                model.secret = form.new_secret.data

    @expose('/refresh/', methods = ('GET', 'POST'))
    def refresh_view(self):
        """
            Refresh key and secret
        """
        return_url = get_redirect_target() or self.get_url('.index_view')

        id = get_mdict_item_or_list(request.args, 'id')
        if id is not None:
            self.get_one(id).refresh()

        return redirect(return_url)


db.create_all()