import os
import warnings

import flask_login as login
from flask import redirect, request, url_for, render_template, send_from_directory
from flask_admin import Admin, AdminIndexView, expose, helpers
from flask_admin.contrib.fileadmin import FileAdmin
from flask_admin.contrib.sqla import ModelView
from flask_principal import identity_changed, Identity, current_app, AnonymousIdentity
from flask_restful import abort
from werkzeug.security import generate_password_hash

import db_control
from env import get_db_dir

# import stub as stub


admin = None


class CVAdminModelView(ModelView):
    '''
    统一数据模型视图
    '''
    list_template = 'model/list.html'
    create_template = 'model/create.html'
    edit_template = 'model/edit.html'
    can_create = False
    can_edit = True
    can_delete = False

    def is_accessible(self):
        '''
        验权处理
        :return:用户是否已经登录
        '''
        return login.current_user.is_authenticated


class CVAdminFileView(FileAdmin):
    '''
    统一文件视图
    '''
    can_delete = False
    can_mkdir = False
    can_rename = False
    allowed_extensions = ('sqlite',)
    column_labels = dict(name = '文件名', size = '大小', date = '修改时间')

    def is_accessible(self):
        '''
        验权处理
        :return: 管理权用户是否已经登录
        '''
        from common.login import admin_permission
        if admin_permission.can():
            return login.current_user.is_authenticated
        else:
            return False


# todo 支持oauth
class CVAdminIndexView(AdminIndexView):
    '''
    主页视图
    '''

    @expose('/')
    def index(self):
        if not login.current_user.is_authenticated:
            # 转入登录页
            return redirect(url_for('.login_view'))

        return redirect(url_for('.dashboard_view'))
        # return self.render('admin/dashboard.html')
        # render_template不会调用admin/base.py中的render方法，导致helpers不会包含在上下文中
        # 没有helpers的引用，在layout.html中set render_ctx = h.resolve_ctx()会出错，最终导致jinja无法对form_rules进行渲染
        # return render_template('admin/dashboard.html', admin_view = self)

    @expose('/login/', methods = ('GET', 'POST'))
    def login_view(self):
        # handle user login
        from common.login import LoginForm
        form = LoginForm(request.form)
        try:
            if helpers.validate_form_on_submit(form):
                user = form.get_user()
                remember = form.remember.data
                login.login_user(user, remember)

            if login.current_user.is_authenticated:
                identity_changed.send(current_app._get_current_object(),
                                      identity = Identity(user.username))
                return redirect(url_for('.index'))
        except:
            pass

        self._template_args['form'] = form

        return render_template('admin/login.html', form = form)

    @expose('/register/', methods = ('GET', 'POST'))
    def register_view(self):
        from common.login import RegistrationForm
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
                              identity = AnonymousIdentity())
        return redirect(url_for('.login_view'))

    @expose('/dashboard/', methods = ('GET', 'POST'))
    def dashboard_view(self):
        from plugins.setting import TargetRule

        if not login.current_user.is_authenticated:
            abort(401)

        records = TargetRule.find_allow_by_user(login.current_user.username)
        targets = {r.target: r.botid for r in records}

        return self.render('admin/dashboard.html', targets = targets)

    @expose('/statistics/', methods = ('GET', 'POST'))
    def statistics_service(self):
        from flask import json
        from common.statistics import get_statistics_data

        return json.dumps(get_statistics_data(request))


def init(app):
    '''
    初始化
    :param app:flask app 
    :return: 
    '''
    global admin
    admin = Admin(
        app,
        name = "云谷机器人控制台",
        index_view = CVAdminIndexView(
            name = '仪表板',
            menu_icon_type = 'fa',
            menu_icon_value = 'dashboard'),
        # base_template = 'admin/layout.html',
        template_mode = 'bootstrap2')

    # Flask views
    @app.route('/')
    def index():
        return render_template("admin/redirect.html")

    # bower_components
    @app.route('/bower_components/<path:path>')
    def send_bower(path):
        return send_from_directory(os.path.join(app.root_path, 'bower_components'), path)

    @app.route('/dist/<path:path>')
    def send_dist(path):
        return send_from_directory(os.path.join(app.root_path, 'dist'), path)

    @app.route('/js/<path:path>')
    def send_js(path):
        return send_from_directory(os.path.join(app.root_path, 'js'), path)

    @app.errorhandler(401)
    def unauthenticated(e):
        return render_template('401.html'), 401

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('403.html'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    # category设置图标
    admin.category_icon_classes = {
        '消息管理': 'fa fa-comments-o',
        '报点管理': 'fa fa-gift',
        '积分管理': 'fa fa-money',
        '统计分析': 'fa fa-bar-chart-o',
        '机器人设置': 'fa fa-reddit',
        '系统设置': 'fa fa-cogs'
    }

    from plugin import hub
    views = {}
    models = {}

    # 从插件中加载已注册的模型类和视图类
    for (hub_k, hub_v) in hub.registry_map.items():
        for (model_k, model_v) in hub_v.model_map.items():
            models[model_k] = model_v
        for (view_k, view_v) in hub_v.view_map.items():
            views[view_k] = view_v

    # 按注册的排序顺序创建数据模型视图
    models_list = [models[k] for k in sorted(models.keys())]
    for model in models_list:
        model_class = model
        view_class = views[model.__name__ + 'View']
        # 不对Fields missing问题提示警告
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', 'Fields missing from ruleset', UserWarning)
            admin.add_view(view_class(model_class, db_control.get_db().session))

    # 创建文件视图
    admin.add_view(CVAdminFileView(get_db_dir(), '', name = '数据库文件', category = '系统设置'))