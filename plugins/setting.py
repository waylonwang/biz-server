# -*- coding: utf-8 -*-
"""
    plugins.admin
    ~~~~~~~~~~~~~~~~


"""
from datetime import datetime

from flask_admin.form import rules
from flask_restful import reqparse, Resource
from pytz import utc
from wtforms import validators, fields

import api_control as ac
import db_control
from app_view import CVAdminModelView
from common.bot import Bot
from plugin import PluginsRegistry
from common.util import get_now, display_datetime, get_botname, get_target_display, get_target_type_choice,\
    get_target_value

__registry__ = cr = PluginsRegistry()

# Model----------------------------------------------------------------------------------------------------
db = db_control.get_db()
api = ac.get_api()

class BotParam(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'bot_param'
    botid = db.Column(db.String(20), primary_key = True)
    name = db.Column(db.String(20), primary_key = True)
    value = db.Column(db.String(100), nullable = False)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    update_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now())
    remark = db.Column(db.String(255), nullable = True)

    @staticmethod
    def create(botid, name, value, remark = None):
        param = BotParam.find(botid, name)
        if not param:
            param = BotParam(botid = botid,
                             name = name,
                             value = value,
                             remark = remark if remark else '')
            param.query.session.add(param)
            param.query.session.commit()
        else:
            param = BotParam.update(botid, name, value, remark)
        return param

    @staticmethod
    def update(botid, name, value, remark = None):
        param = BotParam.find(botid, name)
        if param:
            param.value = value
            if remark:  param.remark = remark
            param.query.session.commit()
        return param

    @staticmethod
    def findall(botid):
        return BotParam.query.filter_by(botid = botid).all()

    @staticmethod
    def find(botid, name):
        return BotParam.query.filter_by(botid = botid, name = name).first()

    @staticmethod
    def delete(botid, name):
        BotParam.query.filter_by(botid = botid, name = name).delete()
        BotParam.query.session.commit()
        return True

class TargetRule(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'target_rule'
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    botid = db.Column(db.String(20), nullable = False)
    type = db.Column(db.String(10), nullable = False)
    target = db.Column(db.String(100), nullable = False)
    create_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now())
    update_at = db.Column(db.DateTime, nullable = False, default = lambda: get_now(), onupdate = lambda: get_now())
    remark = db.Column(db.String(255), nullable = True)

    @staticmethod
    def create(botid, type, target, remark = None):
        rule = TargetRule.find(botid, type, target)
        if not rule:
            rule = TargetRule(botid = botid,
                              type = type,
                              target = target,
                              remark = remark if remark else '')
            rule.query.session.add(rule)
            rule.query.session.commit()
        return rule

    @staticmethod
    def findall(botid, type = None):
        if type:
            return TargetRule.query.filter_by(botid = botid, type = type).all()
        else:
            return TargetRule.query.filter_by(botid = botid).all()

    @staticmethod
    def find(botid, type, target):
        return TargetRule.query.filter_by(botid = botid, type = type, target = target).first()

    @staticmethod
    def find_by_id(id):
        return TargetRule.query.get(id)

    @staticmethod
    def delete(botid, type, target):
        TargetRule.query.filter_by(botid = botid, type = type, target = target).delete()
        TargetRule.query.session.commit()
        return True


db.create_all()


@cr.model('71-BotParam')
def get_botparam_model():
    return BotParam


@cr.model('72-TargetRule')
def get_targetrule_model():
    return TargetRule


# View-----------------------------------------------------------------------------------------------------
class BotParamView(CVAdminModelView):
    column_display_pk = True
    column_filters = ('name',)
    column_labels = dict(botid = '机器人', name = '参数名', value = '参数值', create_at = '创建时间', update_at = '更新时间',
                         remark = '备注')
    column_formatters = dict(
        botid = lambda v, c, m, p: get_botname(m.botid),
        create_at = lambda v, c, m, p: display_datetime(m.create_at),
        update_at = lambda v, c, m, p: display_datetime(m.update_at))
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
        if not current_user.is_admin():
            return super(BotParamView, self).get_query().filter(self.model.botid == current_user.username)
        else:
            return super(BotParamView, self).get_query()
            # if self.session.query(self.model) != None:
            # # return super(SysParamView, self).get_query().filter(self.model.botid == current_user.login)
            #     return self.session.query(self.model).filter(self.model.botid == current_user.login)

    def get_count_query(self):
        from flask_login import current_user
        from flask_admin.contrib.sqla.view import func
        if not current_user.is_admin():
            return self.session.query(func.count('*')).filter(self.model.botid == current_user.username)
        else:
            return super(BotParamView, self).get_count_query()
            # if self.session.query(self.model) != None:
            # return super(SysParamView, self).get_query().filter(self.model.botid == current_user.login)

class TargetRuleView(CVAdminModelView):

    __type_list = {'allow': '允许', 'block': '拒绝'}

    can_create = True
    can_edit = True
    can_delete = True

    column_filters = ('type',)
    column_labels = dict(id = 'ID', botid = '机器人', type = '类型', target = '目标', create_at = '创建时间',
                         update_at = '更新时间',
                         remark = '备注')
    column_formatters = dict(
        create_at = lambda v, c, m, p: display_datetime(m.create_at),
        update_at = lambda v, c, m, p: display_datetime(m.update_at),
        type = lambda v, c, m, p: v.__type_list[m.type],
        target = lambda v, c, m, p: get_target_display(m.target),
        botid = lambda v, c, m, p: get_botname(m.botid)
    )

    form_create_rules = (
        rules.FieldSet(('botid', 'type', 'remark'), '基本信息'),
        rules.FieldSet(('target_type', 'target_account'), '目标设置'),
    )
    form_edit_rules = (
        rules.FieldSet(('botid', 'type', 'remark'), '基本信息'),
        rules.FieldSet(('target_type', 'target_account'), '目标设置'),
    )

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '拦截与放行', '机器人设置')

    def get_query(self):
        from flask_login import current_user
        if not current_user.is_admin():
            return super(TargetRuleView, self).get_query().filter(self.model.botid == current_user.username)
        else:
            return super(TargetRuleView, self).get_query()

    def get_count_query(self):
        from flask_login import current_user
        from flask_admin.contrib.sqla.view import func
        if not current_user.is_admin():
            return self.session.query(func.count('*')).filter(self.model.botid == current_user.username)
        else:
            return super(TargetRuleView, self).get_count_query()

    def get_create_form(self):
        form = self.scaffold_form()
        delattr(form, 'target')
        form.target_type = fields.SelectField('目标类型', coerce = str, choices = get_target_type_choice())
        form.target_account = fields.StringField('目标账号', [validators.required(message = '目标账号是必填字段')])
        form.type = fields.SelectField('类型', [validators.required(message = '类型是必填字段')],
                                       coerce = str, choices = self.__type_list.items())

        def query_factory():
            from flask_login import current_user
            from common.bot import BotAssign
            return [r.botid for r in BotAssign.find_by_user(current_user.username)]

        def get_pk(obj):
            return obj

        def get_label(obj):
            return Bot.find(obj).name

        from wtforms.ext.sqlalchemy.fields import QuerySelectField
        form.botid = QuerySelectField('机器人', [validators.required(message = '机器人是必填字段')],
                                      query_factory = query_factory, get_label = get_label, get_pk = get_pk)
        return form

    def get_edit_form(self):
        form = self.scaffold_form()
        # delattr(form, 'target')
        form.target_type = fields.SelectField('目标类型', [validators.required(message = '目标类型是必填字段')],
                                              coerce = str,
                                              choices = get_target_type_choice())
        form.target_account = fields.StringField('目标账号', [validators.required(message = '目标账号是必填字段')])
        form.type = fields.SelectField('类型', [validators.required(message = '类型是必填字段')],
                                       coerce = str,
                                       choices = self.__type_list.items())
        form.botid = fields.StringField('机器人ID', render_kw = {'readonly': True})
        def query_factory():
            from flask_login import current_user
            from common.bot import BotAssign
            return self.model.find_by_id()

        return form

    def on_model_change(self, form, model, is_created):
        model.target = get_target_value(form.target_type.data,form.target_account.data)

    def on_form_prefill(self, form, id):
        # form.botid.label =  Bot.find(form.botid.data).name
        target = self.model.find_by_id(id).target
        form.target_account.data = target.replace(target[0:2],'')

@cr.view('71-BotParam')
def get_botparam_view():
    return BotParamView


@cr.view('72-TargetRule')
def get_targetrule_view():
    return TargetRuleView


# Control--------------------------------------------------------------------------------------------------
class BotParamsAPI(Resource):
    method_decorators = [ac.require_apikey]

    def get(self):
        try:
            params = BotParam.findall(ac.get_bot())
            result = []
            for param in params:
                result.append({'botid': param.botid,
                               'name': param.name,
                               'value': param.value,
                               'create_at': param.create_at,
                               'update_at': param.update_at,
                               'remark': param.remark})
            return ac.success(params = result)
        except Exception as e:
            return ac.fault(error = e)


class BotParamAPI(Resource):
    method_decorators = [ac.require_apikey]

    def put(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('name', required = True, help = '请求中必须包含name')
            parser.add_argument('value', required = True, help = '请求中必须包含value')
            parser.add_argument('remark')
            args = parser.parse_args()
            param = BotParam.create(ac.get_bot(), args['name'], args['value'], args['remark'])
            if param:
                return ac.success(botid = param.botid,
                                  name = param.name,
                                  value = param.value,
                                  create_at = param.create_at,
                                  update_at = param.update_at,
                                  remark = param.remark)
            else:
                return ac.fault(error = Exception('未知原因导致数据创建失败'))
        except Exception as e:
            return ac.fault(error = e)

    def patch(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('name', required = True, help = '请求中必须包含name')
            parser.add_argument('value', required = True, help = '请求中必须包含value')
            args = parser.parse_args()
            param = BotParam.update(ac.get_bot(), args['name'], args['value'])
            if param:
                return ac.success(botid = param.botid,
                                  name = param.name,
                                  value = param.value,
                                  create_at = param.create_at,
                                  update_at = param.update_at,
                                  remark = param.remark)
            else:
                return ac.fault(error = Exception(ac.get_bot() + '未找到名称为' + args['name'] + '的参数'))
        except Exception as e:
            return ac.fault(error = e)

    def get(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('name', required = True, help = '请求中必须包含name')
            args = parser.parse_args()
            param = BotParam.find(ac.get_bot(), args['name'])
            if param:
                return ac.success(botid = param.botid,
                                  name = param.name,
                                  value = param.value,
                                  create_at = param.create_at,
                                  update_at = param.update_at,
                                  remark = param.remark)
            else:
                return ac.fault(error = Exception(ac.get_bot() + '未找到名称为' + args['name'] + '的参数'))
        except Exception as e:
            return ac.fault(error = e)

    def delete(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('name', required = True, help = '请求中必须包含name')
            args = parser.parse_args()
            result = BotParam.delete(ac.get_bot(), args['name'])
            if result:
                return ac.success(botid = ac.get_bot(), name = args['name'])
            else:
                return ac.fault(error = Exception('未知原因导致数据删除失败'))
        except Exception as e:
            return ac.fault(error = e)


def get_targetrules(type):
    try:
        rules = TargetRule.findall(ac.get_bot(), type)
        result = []
        for rule in rules:
            result.append({'botid': rule.botid,
                           'type': rule.type,
                           'target': rule.target,
                           'create_at': rule.create_at,
                           'update_at': rule.update_at,
                           'remark': rule.remark})
        return ac.success(params = result)
    except Exception as e:
        return ac.fault(error = e)


def put_targetlist(type, target_type):
    try:
        parser = reqparse.RequestParser()
        parser.add_argument('account', required = True, help = '请求中必须包含account')
        parser.add_argument('remark')
        args = parser.parse_args()
        rule = TargetRule.create(ac.get_bot(), type, target_type + '#' + args['account'], args['remark'])
        if rule:
            return ac.success(botid = rule.botid,
                              type = rule.type,
                              target = rule.target,
                              create_at = rule.create_at,
                              update_at = rule.update_at,
                              remark = rule.remark)
        else:
            return ac.fault(error = Exception('未知原因导致数据创建失败'))
    except Exception as e:
        return ac.fault(error = e)


def get_targetrule(type, target_type):
    try:
        parser = reqparse.RequestParser()
        parser.add_argument('account', required = True, help = '请求中必须包含account')
        args = parser.parse_args()
        rule = TargetRule.find(ac.get_bot(), type, target_type + '#' + args['account'])
        if rule:
            return ac.success(botid = rule.botid,
                              type = rule.type,
                              target = rule.target,
                              create_at = rule.create_at,
                              update_at = rule.update_at,
                              remark = rule.remark)
        else:
            return ac.fault(
                error = Exception(ac.get_bot() + '未找到目标为' + target_type + '#' + args['account'] + '的' + type + '规则'))
    except Exception as e:
        return ac.fault(error = e)


def delete_targetrule(type, target_type):
    try:
        parser = reqparse.RequestParser()
        parser.add_argument('account', required = True, help = '请求中必须包含account')
        args = parser.parse_args()
        result = TargetRule.delete(ac.get_bot(), type, target_type + '#' + args['account'])
        if result:
            return ac.success(botid = ac.get_bot(), type = type, target = target_type + '#' + args['account'])
        else:
            return ac.fault(error = Exception('未知原因导致数据删除失败'))
    except Exception as e:
        return ac.fault(error = e)


class AllowsAPI(Resource):
    method_decorators = [ac.require_apikey]

    def get(self):
        return get_targetrules('allow')


class AllowGroupAPI(Resource):
    method_decorators = [ac.require_apikey]

    def put(self):
        return put_targetlist('allow', 'g')

    def get(self):
        return get_targetrule('allow', 'g')

    def delete(self):
        return delete_targetrule('allow', 'g')


class BlocksAPI(Resource):
    method_decorators = [ac.require_apikey]

    def get(self):
        return get_targetrules('block')


class BlockGroupAPI(Resource):
    method_decorators = [ac.require_apikey]

    def put(self):
        return put_targetlist('block', 'g')

    def get(self):
        return get_targetrule('block', 'g')

    def delete(self):
        return delete_targetrule('block', 'g')


api.add_resource(BotParamsAPI, '/botparams', endpoint = 'botparams')
api.add_resource(BotParamAPI, '/botparam', endpoint = 'botparam')
api.add_resource(AllowsAPI, '/allow_list', endpoint = 'allowlist')
api.add_resource(AllowGroupAPI, '/allow_group', endpoint = 'allowgroup')
api.add_resource(BlocksAPI, '/block_list', endpoint = 'blocklist')
api.add_resource(BlockGroupAPI, '/block_group', endpoint = 'blockgroup')