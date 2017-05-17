import flask_login as login

from app_view import CVAdminModelView
from plugin import PluginsRegistry

__registry__ = cr = PluginsRegistry()

class UserView(CVAdminModelView):
    can_create = True
    can_edit = True
    can_delete = True
    # inline_models = [(Role, dict(form_columns=['id', 'name']))]
    column_list = ('id','username','password','email','roles' )
    column_labels = dict(id='用户ID', username='用户名', password='密码', email='邮箱地址',roles='角色')
    column_formatters = dict(password = lambda v, c, m, p: '••••••')
    # ,roles = lambda v, c, m, p: str(m.roles).replace('[<Model Role `','').replace('`>]',''))

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '用户','系统设置')

    def is_accessible(self):
        from common.login_control import admin_permission
        if admin_permission.can():
            return login.current_user.is_authenticated
        else:
            return False

class RoleView(CVAdminModelView):
    can_create = True
    can_edit = True
    can_delete = True
    # column_auto_select_related = True
    from common.login_model import User
    # inline_models =[(User, dict(
    #     column_descriptions=dict(users='用户')
    # ))]
    inline_models = [(User, dict(form_columns=['id', 'username','email']))]
    # column_list = ('id', 'name', 'description')
    column_labels = dict(id='角色ID', name='角色名', description='详述')

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '角色','系统设置')

    def is_accessible(self):
        from common.login_control import admin_permission
        if admin_permission.can():
            return login.current_user.is_authenticated
        else:
            return False

@cr.view('91-Role')
def get_role_view():
    return RoleView


@cr.view('92-User')
def get_user_view():
    return UserView
