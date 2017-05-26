import warnings

import flask_login as login
from flask import redirect, request, url_for, render_template
from flask_admin import Admin, AdminIndexView, expose, helpers
from flask_admin.contrib.fileadmin import FileAdmin
from flask_admin.contrib.sqla import ModelView
from flask_principal import identity_changed, Identity, current_app, AnonymousIdentity
from werkzeug.security import generate_password_hash

import db_control
from env import get_db_dir

admin = None


class CVAdminModelView(ModelView):
    can_create = False
    can_edit = True
    can_delete = False

    def is_accessible(self):
        return login.current_user.is_authenticated


class CVAdminFileView(FileAdmin):
    can_delete = False
    can_mkdir = False
    can_rename = False
    allowed_extensions = ('sqlite',)
    column_labels = dict(name='文件名', size='大小', date='修改时间')

    def is_accessible(self):
        from common.login_control import admin_permission
        if admin_permission.can():
            return login.current_user.is_authenticated
        else:
            return False

# todo 支持oauth
# Create customized index view class that handles login & registration
class CVAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))
        return super(CVAdminIndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        # handle user login
        from common.login_control import LoginForm
        form = LoginForm(request.form)
        if helpers.validate_form_on_submit(form):
            user = form.get_user()
            login.login_user(user)

        if login.current_user.is_authenticated:
            identity_changed.send(current_app._get_current_object(),
                                  identity=Identity(user.username))
            return redirect(url_for('.index'))
        # link = '<p>Don\'t have an account?
        # <a href="' + url_for('.register_view') + '">Click here to register.</a></p>'
        self._template_args['form'] = form
        # self._template_args['link'] = link
        return super(CVAdminIndexView, self).index()

    @expose('/register/', methods=('GET', 'POST'))
    def register_view(self):
        from common.login_control import RegistrationForm
        form = RegistrationForm(request.form)
        if helpers.validate_form_on_submit(form):
            from common.user import User
            user = User()

            form.populate_obj(user)
            # we hash the users password to avoid saving it as plaintext in the db,
            # remove to use plain text:
            user.password = generate_password_hash(form.password.data)

            db_control.get_db().session.add(user)
            db_control.get_db().session.commit()

            login.login_user(user)
            return redirect(url_for('.index'))
        link = '<p>Already have an account? <a href="' + url_for('.login_view') + '">Click here to log in.</a></p>'
        self._template_args['form'] = form
        self._template_args['link'] = link
        return super(CVAdminIndexView, self).index()

    @expose('/logout/')
    def logout_view(self):
        login.logout_user()
        identity_changed.send(current_app._get_current_object(),
                              identity=AnonymousIdentity())
        return redirect(url_for('.index'))


def init(app):
    global admin
    admin = Admin(app, name="云谷机器人管理系统", index_view=CVAdminIndexView(), base_template='my_master.html',
                  template_mode='bootstrap3')

    # Flask views
    @app.route('/')
    def index():
        return render_template('index.html')

    from plugin import hub
    views = {}
    models = {}
    for (hub_k, hub_v) in hub.registry_map.items():
        for (model_k, model_v) in hub_v.model_map.items():
            models[model_k] = model_v
        for (view_k, view_v) in hub_v.view_map.items():
            views[view_k] = view_v

    views = [(k, views[k]) for k in sorted(views.keys())]
    for view in views:
        id = view[0]
        model_class = models[id]()
        view_class = view[1]()
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', 'Fields missing from ruleset', UserWarning)
            admin.add_view(view_class(model_class, db_control.get_db().session))

    admin.add_view(CVAdminFileView(get_db_dir(), '/data/db/', name='数据库文件', category='系统设置'))
