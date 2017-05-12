# -*- coding: utf-8 -*-
"""
    plugins.admin
    ~~~~~~~~~~~~~~~~


"""
from datetime import datetime

from pytz import utc
from sqlalchemy import Integer, String

import db_control
from app_view import CVAdminModelView
from plugin import PluginsRegistry

__registry__ = cr = PluginsRegistry()

# Model----------------------------------------------------------------------------------------------------
db = db_control.get_db()


class SysParam(db.Model):
    __bind_key__ = 'default'
    __tablename__ = 'sys_params'
    botid = db.Column(String(20), primary_key=True)
    name = db.Column(String(20), primary_key=True)
    value = db.Column(String(100), nullable=False)
    createtime = db.Column(Integer, nullable=False)
    updatetime = db.Column(Integer, nullable=False, default=int(datetime.now(tz=utc).timestamp()))
    remark = db.Column(String(255), nullable=True)


class TargetRule(db.Model):
    __bind_key__ = 'default'
    __tablename__ = 'target_list'
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    botid = db.Column(String(20), nullable=False)
    type = db.Column(String(10), nullable=False)
    target = db.Column(String(100), nullable=False)
    createtime = db.Column(Integer, nullable=False)
    updatetime = db.Column(Integer, nullable=False, default=int(datetime.now(tz=utc).timestamp()))
    remark = db.Column(String(255), nullable=True)


db.create_all()


@cr.model('71-SysParam')
def get_sysparam_model():
    return SysParam


@cr.model('72-TargetRule')
def get_targetrule_model():
    return TargetRule


# View-----------------------------------------------------------------------------------------------------
class SysParamView(CVAdminModelView):
    column_filters = ('name',)
    column_labels = dict(botid='机器人ID', name='参数名', value='参数值', createtime='创建时间', updatetime='更新时间', remark='备注')
    column_formatters = dict(createtime=lambda v, c, m, p: datetime.fromtimestamp(m.createtime).strftime('%Y-%m-%d'),
                             updatetime=lambda v, c, m, p: datetime.fromtimestamp(m.updatetime).strftime('%Y-%m-%d'))
    form_columns = ('value', 'remark')

    # from login.login_control import admin_permission
    # try:
    #     if admin_permission.can():
    #         can_create = True
    #         can_edit = True
    #         can_delete = True
    #     else:
    #         can_create = False
    #         can_edit = False
    #         can_delete = False
    # except:
    #     can_create = False
    #     can_edit = False
    #     can_delete = False

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '机器人参数', '机器人设置')

    def get_query(self):
        from flask_login import current_user
        if current_user.username != 'admin':
            return super(SysParamView, self).get_query().filter(self.model.botid == current_user.username)
        else:
            return super(SysParamView, self).get_query()
            # if self.session.query(self.model) != None:
            # # return super(SysParamView, self).get_query().filter(self.model.botid == current_user.login)
            #     return self.session.query(self.model).filter(self.model.botid == current_user.login)

    def get_count_query(self):
        from flask_login import current_user
        from flask_admin.contrib.sqla.view import func
        if current_user.username != 'admin':
            return self.session.query(func.count('*')).filter(self.model.botid == current_user.username)
        else:
            return super(SysParamView, self).get_count_query()
            # if self.session.query(self.model) != None:
            # return super(SysParamView, self).get_query().filter(self.model.botid == current_user.login)


class TargetRuleView(CVAdminModelView):
    can_create = True
    can_edit = True
    can_delete = True
    column_filters = ('type',)
    column_labels = dict(id='ID', botid='机器人ID', type='类型', target='目标', createtime='创建时间', updatetime='更新时间',
                         remark='备注')
    column_formatters = dict(createtime=lambda v, c, m, p: datetime.fromtimestamp(m.createtime).strftime('%Y-%m-%d'),
                             updatetime=lambda v, c, m, p: datetime.fromtimestamp(m.updatetime).strftime('%Y-%m-%d'))
    # column_type_formatters = MY_DEFAULT_FORMATTERS
    form_columns = ('type', 'target', 'createtime', 'updatetime', 'remark')
    form_args = dict(
        # createtime = dict(validators=[DataRequired()], format='%Y-%m-%d'),
        # updatetime = dict(validators=[DataRequired()], format='%Y-%m-%d')
    )
    form_edit_rules = ('type', 'target', 'updatetime', 'remark')
    form_create_rules = ('type', 'target', 'createtime', 'remark')
    form_widget_args = {
        'createtime': {
            'disabled': True,
            'data-date-format': u'YYYY-MM-DD'
        },
        'updatetime': {
            'disabled': True,
            'data-date-format': u'YYYY-MM-DD'
        }
    }

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '拦截与放行', '机器人设置')

    def get_query(self):
        from flask_login import current_user
        if current_user.username != 'admin':
            return super(TargetRuleView, self).get_query().filter(self.model.botid == current_user.username)
        else:
            return super(TargetRuleView, self).get_query()

    def get_count_query(self):
        from flask_login import current_user
        from flask_admin.contrib.sqla.view import func
        if current_user.username != 'admin':
            return self.session.query(func.count('*')).filter(self.model.botid == current_user.username)
        else:
            return super(TargetRuleView, self).get_count_query()


@cr.view('71-SysParam')
def get_sysparam_view():
    return SysParamView


@cr.view('72-TargetRule')
def get_targetrule_view():
    return TargetRuleView

# Control--------------------------------------------------------------------------------------------------
