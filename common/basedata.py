import flask_login as login

import db_control
from app_view import CVAdminModelView
from common.util import get_now, display_datetime
from plugin import PluginsRegistry

__registry__ = pr = PluginsRegistry()

db = db_control.get_db()


@pr.register_model(91)
class Basedata(db.Model):
    __bind_key__ = 'default'
    __tablename__ = 'base_data'

    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    code = db.Column(db.String(20), nullable = False, unique = True)
    name = db.Column(db.String(20), nullable = False)
    value = db.Column(db.String(255), nullable = True)
    type = db.Column(db.Integer, nullable = False, default = 0)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    update_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now())
    remark = db.Column(db.String(255), nullable = True)

    @staticmethod
    def findall():
        return Basedata.query.all()

    @staticmethod
    def find_by_type(type):
        return Basedata.query.filter_by(type = type).all()

    @staticmethod
    def find_by_code(code):
        return Basedata.query.filter_by(code = code).first()

    @staticmethod
    def find(id):
        return Basedata.query.get(id)

@pr.register_view()
class BasedataView(CVAdminModelView):
    can_create = True
    can_edit = True
    can_delete = True

    column_labels = dict(code = '代码', name = '名称', value = '值', type = '类型', create_at = '创建时间', update_at = '更新时间',
                         remark = '备注')
    column_formatters = dict(create_at = lambda v, c, m, p: display_datetime(m.create_at),
                             update_at = lambda v, c, m, p: display_datetime(m.update_at))
    form_edit_rules = ('type', 'code', 'name', 'value', 'remark')
    form_create_rules = ('type', 'code', 'name', 'value', 'remark')

    column_default_sort = ('type')

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '基础数据', '系统设置')

    def is_accessible(self):
        from common.login import admin_permission
        if admin_permission.can():
            return login.current_user.is_authenticated
        else:
            return False

            # def get_create_form(self):
            #     form = self.scaffold_form()
            #     form.id = StringField('机器人ID', [validators.required(message = '机器人ID是必填字段')])
            #     form.active = fields.BooleanField('启用状态', [validators.required(message = '启用状态是必填字段')])
            #     return form
            #
            # def get_edit_form(self):
            #     form = self.scaffold_form()
            #     form.id = StringField('机器人ID', render_kw = {'readonly': True})
            #     form.active = fields.BooleanField('启用状态', [validators.required(message = '启用状态是必填字段')])
            #     return form


db.create_all()