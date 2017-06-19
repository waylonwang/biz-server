import datetime
import math
import os
import warnings

import flask_login as login
from flask import redirect, request, url_for, render_template, send_from_directory
from flask_admin import Admin, AdminIndexView, expose, helpers
from flask_admin.contrib.fileadmin import FileAdmin
from flask_admin.contrib.sqla import ModelView
from flask_principal import identity_changed, Identity, current_app, AnonymousIdentity
from werkzeug.security import generate_password_hash

import db_control
from common.util import target_prefix2name, get_now, output_datetime, get_CQ_display
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

    @expose('/dashboard/', methods = ('GET', 'POST'))
    def dashboard_view(self):
        from plugins.speak import Speak, SpeakCount
        from plugins.sign import Sign
        from plugins.point import Point
        from plugins.score import ScoreRecord
        from plugins.setting import TargetRule

        today = output_datetime(get_now(), True, False)
        max_speaks = 0
        mix_speaks = 0
        speak_statistics = {}
        speak_tops = {}
        speak_today_count = 0
        sign_today_count = 0
        point_today_total = 0
        score_today_total = 0

        def get_score_today_total(score_today_total, target, today):
            score_today = ScoreRecord.get_flow(target.botid, target_prefix2name(target.target.split('#')[0]),
                                               target.target.split('#')[1], today, today)
            if score_today.total is not None:
                score_today_total += score_today.total
            return score_today_total

        def get_point_today_total(point_today_total, target, today):
            point_today = Point.get_total(target.botid, target_prefix2name(target.target.split('#')[0]),
                                          target.target.split('#')[1], today, today)
            if point_today.total_success is not None:
                point_today_total += point_today.total_success
            return point_today_total

        def get_sign_today_count(sign_today_count, target, today):
            sign_today = Sign.get_count(target.botid, target_prefix2name(target.target.split('#')[0]),
                                        target.target.split('#')[1], today, today)
            if sign_today.cnt is not None:
                sign_today_count += sign_today.cnt
            return sign_today_count

        def get_speak_statistics(speak_statistics, target, today):
            max_count = 0
            mix_count = 0
            statistics_data = SpeakCount.statistics(target.botid,
                                                    target_prefix2name(target.target.split('#')[0]),
                                                    target.target.split('#')[1],
                                                    output_datetime(get_now() - datetime.timedelta(days = 60), True,
                                                                    False),
                                                    today).fetchall()
            if len(statistics_data) > 0:
                speak_statistics[target.target] = [statistics_data,target.botid]
                for r in statistics_data:
                    max_count = max(max_count, int(r.message_count))
                    mix_count = min(mix_count if mix_count !=0 else max_count, int(r.vaild_count))

            return max_count, mix_count

        def get_speak_tops(speak_tops, target, today):
            records = Speak.get_top(target.botid,
                                    target_prefix2name(target.target.split('#')[0]),
                                    target.target.split('#')[1],
                                    today,
                                    today)
            top_data = [{'name': get_CQ_display(r.sender_name), 'id': r.sender_id, 'count': r.cnt} for r in records]
            if len(top_data) > 0:
                speak_tops[target.target] = top_data

        def get_speak_today_count(speak_today_count, target, today):
            speak_today = Speak.get_count(target.botid, target_prefix2name(target.target.split('#')[0]),
                                          target.target.split('#')[1], today, today)
            if speak_today.cnt_full is not None:
                speak_today_count += speak_today.cnt_full
            return speak_today_count

        targets = TargetRule.find_allow_by_user(login.current_user.username)
        for target in targets:
            speak_today_count = get_speak_today_count(speak_today_count, target, today)
            sign_today_count = get_sign_today_count(sign_today_count, target, today)
            point_today_total = get_point_today_total(point_today_total, target, today)
            score_today_total = get_score_today_total(score_today_total, target, today)
            speak_statistics_count = get_speak_statistics(speak_statistics, target, today)
            get_speak_tops(speak_tops, target, today)
            max_speaks = max(max_speaks, speak_statistics_count[0])
            mix_speaks = min(mix_speaks if mix_speaks !=0 else max_speaks, speak_statistics_count[1])

        return self.render('admin/dashboard.html',
                           today = today,
                           max_speaks = math.ceil(max_speaks / 100) * 100,
                           mix_speaks = math.floor(mix_speaks / 100) * 100,
                           speak_today_count = speak_today_count,
                           sign_today_count = sign_today_count,
                           point_today_total = point_today_total,
                           score_today_total = score_today_total,
                           speak_statistics = speak_statistics,
                           speak_tops = speak_tops)

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