import flask_login as login
from flask import url_for, redirect, request, flash
from flask_admin import expose
from flask_admin.form import rules, FormOpts
from flask_admin.helpers import get_redirect_target
from flask_admin.model.helpers import get_mdict_item_or_list
from flask_admin.model.template import TemplateLinkRowAction, EndpointLinkRowAction
from flask_babelex import gettext
from markupsafe import Markup
from werkzeug.security import generate_password_hash
from wtforms import validators, fields, HiddenField
from wtforms.validators import DataRequired

import db_control
from app_view import CVAdminModelView
from common.util import get_now, display_datetime, get_yesno_display
from plugin import PluginsRegistry

__registry__ = pr = PluginsRegistry()

# Model----------------------------------------------------------------------------------------------------
db = db_control.get_db()

users_roles = db.Table('users_roles',
                       db.Column('username', db.String(45), db.ForeignKey('users.username')),
                       db.Column('role_id', db.String(45), db.ForeignKey('roles.id')))


@pr.register_model(92)
class Role(db.Model):
    __bind_key__ = 'default'
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    name = db.Column(db.String(255), nullable = False, unique = True)
    description = db.Column(db.String(255), nullable = True)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    update_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now())

    def __init__(self, **kwargs):
        if kwargs is not None:
            if kwargs.get('name', None) is not None:
                self.name = kwargs['name']
            if kwargs.get('description', None) is not None:
                self.description = kwargs['description']

    def __repr__(self):
        # return "<Model Role `{}`>".format(self.name)
        return self.name

    @staticmethod
    def is_admin(roles):
        for role in roles:
            if role.name == 'admin':
                return True
        return False

    @staticmethod
    def find_by_name(name):
        return Role.query.filter_by(name = name).first()
        # return Role.query.get(username)


# Create user model.
@pr.register_model(93)
class User(db.Model):
    __bind_key__ = 'default'
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    username = db.Column(db.String(255), nullable = False, unique = True)
    password = db.Column(db.String(64), nullable = True)
    email = db.Column(db.String(120), nullable = True)
    active = db.Column(db.Integer, nullable = False, default = 1, index = True)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    update_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now())
    remark = db.Column(db.String(255), nullable = True)

    roles = db.relationship(
        'Role',
        secondary = users_roles,
        backref = db.backref('users', lazy = 'dynamic'))

    def __init__(self, **kwargs):
        if kwargs is not None:
            if kwargs.get('username', None) is not None:
                self.username = kwargs['username']

                if kwargs.get('password', None) is None:
                    kwargs['password'] = 'password'
                self.password = kwargs['password']

                if kwargs.get('rolename', None) is None:
                    kwargs['rolename'] = 'user'
                role = Role.query.filter_by(name = kwargs['rolename']).one()
                self.roles.append(role)

                if kwargs.get('remark', None) is not None:
                    self.remark = kwargs['remark']

    def __repr__(self):
        """Define the string format for instance of User."""
        return "<Model User `{}`>".format(self.username)

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return self.active

    def is_anonymous(self):
        return False

    def is_admin(self):
        for role in self.roles:
            if role.name == 'admin':
                return True
        return False

    def get_id(self):
        return self.id

    # Required for administrative interface
    def __unicode__(self):
        return self.username

    @staticmethod
    def find_by_name(username):
        # return User.query.filter_by(username = username).first()
        return User.query.get(username)

    @staticmethod
    def find_by_role(rolename):
        role = Role.find_by_name(rolename)
        if role is not None:
            session = db.session
            cnts = session.execute('SELECT count(1) cnt FROM users_roles WHERE role_id = :id', {'id': role.id})
            if cnts is not None:
                return cnts.first()
        return None
        # return User.query.get(username)

    @staticmethod
    def findall():
        return User.query.filter_by(active = 1).all()


def init(**kwargs):
    db.create_all()
    user_cnt = User.find_by_role('admin')
    if user_cnt is None or user_cnt.cnt == 0:
        admin_role = Role(name = 'admin', description = '管理员角色')
        user_role = Role(name = 'user', description = '缺省用户角色')
        db.session.add(admin_role)
        db.session.add(user_role)
        db.session.commit()
        admin_user = User(username = 'admin', password = generate_password_hash('admin'), rolename = 'admin',
                          remark = '超级管理员')
        db.session.add(admin_user)
        db.session.commit()

    return


db.create_all()


# View-----------------------------------------------------------------------------------------------------
@pr.register_view()
class UserView(CVAdminModelView):
    can_create = True
    can_edit = True
    can_delete = True
    # inline_models = [(Role, dict(form_columns=['id', 'name']))]
    column_list = ('id', 'username', 'password', 'email', 'roles', 'active', 'create_at', 'update_at', 'remark')
    column_labels = dict(id = '用户ID', username = '用户名', password = '密码',
                         email = '邮箱地址', roles = '角色', active = '启用',
                         create_at = '创建时间', update_at = '更新时间', remark = '备注')
    column_filters = ('roles.name',)
    column_formatters = dict(password = lambda v, c, m, p: '••••••',
                             active = lambda v, c, m, p: get_yesno_display(m.active),
                             create_at = lambda v, c, m, p: display_datetime(m.create_at),
                             update_at = lambda v, c, m, p: display_datetime(m.update_at))

    # def get_action_url(self):
    #     self.get_url('.edit_view', id = self.get_pk_value(self.row),
    #                  url = get_redirect_target() or self.get_url('.index_view'))

    column_extra_row_actions = [
        # LinkRowAction('fa fa-key','/admin/user/edit/?id={row_id}&amp;url=%2Fadmin%2Fuser%2F'),
        EndpointLinkRowAction('fa fa-key', 'user.resetpass_view',title='重置密码')
    ]

    form_args = dict(
        roles = dict(validators = [DataRequired()])
    )
    form_create_rules = (
        rules.FieldSet(('username', 'email', 'remark'), '基本信息'),
        # rules.FieldSet(('roles', 'apikey', 'active'), 'Permission'),
        rules.FieldSet(('roles', 'active'), '权限设置'),
        # rules.FieldSet(('password', 'password_confirm'), '账号安全')
    )

    form_edit_rules = (
        rules.FieldSet(('username', 'email', 'remark'), '基本信息'),
        rules.FieldSet(('roles', 'active'), '权限设置'),
        # rules.Header('重置密码'),
        # rules.FieldSet(('new_password', 'new_password_confirm'), '重置密码')
        # rules.Field()
    )

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '用户', '系统设置')

    def is_accessible(self):
        from common.login import admin_permission
        if request.endpoint == 'user.resetpass_view':
            if (login.current_user.id == int(request.values.get('id'))) or admin_permission.can():
                return login.current_user.is_authenticated
            else:
                return False
        else:
            if admin_permission.can():
                return login.current_user.is_authenticated
            else:
                return False

    def get_create_form(self):
        form = self.scaffold_form()
        form.username = fields.StringField('用户名', [validators.required(message = '用户名是必填字段')])
        # form.password = fields.PasswordField('密码', [validators.required(message = '密码是必填字段')])
        # form.password_confirm = fields.PasswordField('密码确认',
        #                                              [validators.required(message = '密码是必填字段'),
        #                                               validators.equal_to(fieldname = 'password',
        #                                                                   message = '确认密码须一致')])
        form.active = fields.BooleanField('启用状态', [validators.required(message = '启用状态是必填字段')], default = True)
        return form

    def get_edit_form(self):
        form = self.scaffold_form()
        delattr(form, 'password')
        # form.new_password = fields.PasswordField('新密码')
        # form.new_password_confirm = fields.PasswordField('密码确认',
        #                                                  [validators.equal_to(fieldname = 'new_password',
        #                                                                       message = '确认密码须一致')])
        form.active = fields.BooleanField('启用状态', [validators.required(message = '启用状态是必填字段')], default = True)
        return form

    def on_model_change(self, form, model, is_created):
        if not is_created:
            if hasattr(form,'new_password'):
                model.password = generate_password_hash(form.new_password.data)
        else:
            model.password = generate_password_hash(model.password)

    def get_action_form(self):
        '''
            定制Action
        :return: 
        '''
        class ResetpassForm(self.form_base_class):
            form_widget_args = {}
            form_edit_rules = [
                rules.Field('new_password'),
                rules.Field('new_password_confirm')
            ]
            _form_edit_rules = rules.RuleSet(self, form_edit_rules)
            action = HiddenField('')
            url = HiddenField('')
            new_password = fields.PasswordField('新密码',[validators.required(message = '密码是必填字段')])
            new_password_confirm = fields.PasswordField('密码确认',
                                                        [validators.equal_to(fieldname = 'new_password',
                                                                             message = '确认密码须一致')])

        return ResetpassForm

    @expose('/resetpass/', methods = ('GET', 'POST'))
    def resetpass_view(self):
        """
            Reset password view
        """
        return_url = get_redirect_target() or self.get_url('.index_view')

        if not self.can_edit:
            return redirect(return_url)

        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return redirect(return_url)

        model = self.get_one(id)

        if model is None:
            flash(gettext('Record does not exist.'), 'error')
            return redirect(return_url)

        form = self.action_form(obj = model)

        if not hasattr(form, '_validated_ruleset') or not form._validated_ruleset:
            self._validate_form_instance(ruleset = form._form_edit_rules, form = form)

        if self.validate_form(form):
            if self.update_model(form, model):
                flash(gettext('Record was successfully saved.'), 'success')
                if '_add_another' in request.form:
                    return redirect(self.get_url('.create_view', url = return_url))
                elif '_continue_editing' in request.form:
                    return redirect(request.url)
                else:
                    # save button
                    return redirect(self.get_save_return_url(model, is_created = False))

        if request.method == 'GET' or form.errors:
            self.on_form_prefill(form, id)

        form_opts = FormOpts(widget_args = form.form_widget_args,
                             form_rules = form._form_edit_rules)

        template = 'model/resetpass.html'

        return self.render(template,
                           model = model,
                           form = form,
                           form_opts = form_opts,
                           return_url = return_url)


@pr.register_view()
class RoleView(CVAdminModelView):
    can_create = True
    can_edit = True
    can_delete = True
    # column_auto_select_related = True
    # from common.user import User
    # # inline_models =[(User, dict(
    # #     column_descriptions=dict(users='用户')
    # # ))]
    # # inline_models = [(User, dict(form_columns = ['id', 'username', 'email']))]
    #
    # from flask_admin.model.form import InlineFormAdmin
    # class MyInlineModelForm(InlineFormAdmin):
    #     form_columns = ('id', 'username', 'email', 'active', 'remark')
    #     # column_labels = dict(id = '用户ID', username = '用户名', password = '密码',
    #     #                      email = '邮箱地址', roles = '角色', active = '启用',
    #     #                      create_at = '创建时间', update_at = '更新时间', remark = '备注')
    #
    #     def postprocess_form(self, form):
    #         # form_create_rules = (
    #         #     rules.FieldSet(('username', 'email','remark'), '基本信息'),
    #         #     rules.FieldSet(('active',), '权限设置'),
    #         # )
    #         # self._form_rules = rules.RuleSet(self, form_create_rules)
    #         form.username = fields.StringField('用户名', [validators.required(message = '用户名是必填字段')])
    #         form.email = fields.StringField('邮箱地址')
    #         form.active = fields.BooleanField('启用状态', [validators.required(message = '启用状态是必填字段')], default = True)
    #         form.remark = fields.StringField('备注')
    #         return form
    #
    # inline_models = (MyInlineModelForm(User),)

    column_list = ('id', 'name', 'description', 'users_count', 'create_at', 'update_at')
    column_labels = dict(id = '角色ID', name = '角色名', description = '详述',
                         create_at = '创建时间', update_at = '更新时间', users_count = '用户数', users = '用户')

    def _user_formatter(view, context, model, name):
        cnt = User.find_by_role(model.name)
        if cnt is not None:
            return Markup(
                u"<a href= '%s'>%s</a>" % (
                    url_for('user.index_view', flt1_0 = model.name),
                    cnt[0]
                )
            )
        else:
            return 0

    column_formatters = dict(create_at = lambda v, c, m, p: display_datetime(m.create_at),
                             update_at = lambda v, c, m, p: display_datetime(m.update_at),
                             users_count = _user_formatter)
    form_columns = ('name', 'description')

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '角色', '系统设置')

    def is_accessible(self):
        from common.login import admin_permission
        if admin_permission.can():
            return login.current_user.is_authenticated
        else:
            return False