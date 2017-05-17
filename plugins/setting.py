# -*- coding: utf-8 -*-
"""
    plugins.admin
    ~~~~~~~~~~~~~~~~


"""
from datetime import datetime

from flask_restful import reqparse, Resource
from pytz import utc

import api_control as ac
import db_control
from app_view import CVAdminModelView
from plugin import PluginsRegistry

__registry__ = cr = PluginsRegistry()

# Model----------------------------------------------------------------------------------------------------
db = db_control.get_db()
api = ac.get_api()


class BotParam(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'sys_params'
    botid = db.Column(db.String(20), primary_key = True)
    name = db.Column(db.String(20), primary_key = True)
    value = db.Column(db.String(100), nullable = False)
    createtime = db.Column(db.Integer, nullable = False, default = int(datetime.now(tz = utc).timestamp()))
    updatetime = db.Column(db.Integer, nullable = False, default = int(datetime.now(tz = utc).timestamp()))
    remark = db.Column(db.String(255), nullable = True)

    @staticmethod
    def create(botid, name, value, remark = None):
        param = BotParam.find(botid, name)
        if not param:
            param = BotParam(botid = botid,
                             name = name,
                             value = value,
                             createtime = int(datetime.now(tz = utc).timestamp()),
                             updatetime = int(datetime.now(tz = utc).timestamp()),
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
            param.updatetime = int(datetime.now(tz = utc).timestamp())
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
    __tablename__ = 'target_list'
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    botid = db.Column(db.String(20), nullable = False)
    type = db.Column(db.String(10), nullable = False)
    target = db.Column(db.String(100), nullable = False)
    createtime = db.Column(db.Integer, nullable = False, default = int(datetime.now(tz = utc).timestamp()))
    updatetime = db.Column(db.Integer, nullable = False, default = int(datetime.now(tz = utc).timestamp()))
    remark = db.Column(db.String(255), nullable = True)

    @staticmethod
    def create(botid, type, target, remark = None):
        rule = TargetRule.find(botid, type, target)
        if not rule:
            rule = TargetRule(botid = botid,
                              type = type,
                              target = target,
                              createtime = int(datetime.now(tz = utc).timestamp()),
                              updatetime = int(datetime.now(tz = utc).timestamp()),
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
    column_labels = dict(botid = '机器人ID', name = '参数名', value = '参数值', createtime = '创建时间', updatetime = '更新时间',
                         remark = '备注')
    column_formatters = dict(
        createtime = lambda v, c, m, p: datetime.fromtimestamp(m.createtime).strftime('%Y-%m-%d'),
        updatetime = lambda v, c, m, p: datetime.fromtimestamp(m.updatetime).strftime('%Y-%m-%d'))
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
            return super(BotParamView, self).get_query().filter(self.model.botid == current_user.username)
        else:
            return super(BotParamView, self).get_query()
            # if self.session.query(self.model) != None:
            # # return super(SysParamView, self).get_query().filter(self.model.botid == current_user.login)
            #     return self.session.query(self.model).filter(self.model.botid == current_user.login)

    def get_count_query(self):
        from flask_login import current_user
        from flask_admin.contrib.sqla.view import func
        if current_user.username != 'admin':
            return self.session.query(func.count('*')).filter(self.model.botid == current_user.username)
        else:
            return super(BotParamView, self).get_count_query()
            # if self.session.query(self.model) != None:
            # return super(SysParamView, self).get_query().filter(self.model.botid == current_user.login)


class TargetRuleView(CVAdminModelView):
    can_create = True
    can_edit = True
    can_delete = True

    column_filters = ('type',)
    column_labels = dict(id = 'ID', botid = '机器人ID', type = '类型', target = '目标', createtime = '创建时间',
                         updatetime = '更新时间',
                         remark = '备注')
    column_formatters = dict(
        createtime = lambda v, c, m, p: datetime.fromtimestamp(m.createtime).strftime('%Y-%m-%d'),
        updatetime = lambda v, c, m, p: datetime.fromtimestamp(m.updatetime).strftime('%Y-%m-%d'))
    # column_type_formatters = MY_DEFAULT_FORMATTERS
    form_columns = ('type', 'target', 'remark')
    form_args = dict(
        # createtime = dict(validators=[DataRequired()], format='%Y-%m-%d'),
        # updatetime = dict(validators=[DataRequired()], format='%Y-%m-%d')
    )
    form_edit_rules = ('type', 'target', 'remark')
    form_create_rules = ('type', 'target', 'remark')
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
                               'createtime': param.createtime,
                               'updatetime': param.updatetime,
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
                                  createtime = param.createtime,
                                  updatetime = param.updatetime,
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
                                  createtime = param.createtime,
                                  updatetime = param.updatetime,
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
                                  createtime = param.createtime,
                                  updatetime = param.updatetime,
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
                           'createtime': rule.createtime,
                           'updatetime': rule.updatetime,
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
                              createtime = rule.createtime,
                              updatetime = rule.updatetime,
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
                              createtime = rule.createtime,
                              updatetime = rule.updatetime,
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