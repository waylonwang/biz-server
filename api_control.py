from functools import wraps

from flask import request
from flask_restful import Api
from werkzeug.exceptions import HTTPException

_api = None


def init(app):
    global _api
    _api = Api(app)
    return _api


def set_api(api):
    global _api
    _api = api


def get_api():
    global _api
    return _api


def get_apikey():
    if not request.headers.get('Authorization'):
        return None
    try:
        auth = eval(request.headers.get('Authorization'))
        if not auth.get('api_key'):
            return None
        from common.apikey import APIKey
        return APIKey.find_by_key(auth.get('api_key'))
    except:
        return None


def get_bot():
    key = get_apikey()
    if key:
        return key.botid
    else:
        return None


def require_apikey(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not get_apikey():
            return fault(code = 1001)
        return func(*args, **kwargs)

    return wrapper


def register_api(*urls, **kwargs):
    def decorator(cls):
        global _api
        _api.add_resource(cls, *urls, **kwargs)

        return cls

    return decorator


def success(httpstatus = 200, **kwargs):
    '''
    :param kwargs: 数据正文
    :return: 
    '''
    return {'success': 1,
            'code': 0,
            'message': '',
            'data': kwargs}, httpstatus


def fault(**kwargs):
    '''
    :param code: 错误码 1001:API Key不合法 1002:权限错误 2001:HTTP请求错误 3001:一般运行错误 
    :param message: 错误信息
    :return: 
    '''
    error = kwargs.get('error')
    code = kwargs.get('code')
    message = ''
    status = 500
    if code == 1001:
        status = 401
        code = 1001
        message = 'API Key不合法，请检查请求header中的Authorization是否已包含合法的api_key'
    else:
        if isinstance(error, HTTPException):
            status = error.code
            code = 2001
            message = error.data.get('message')
        else:
            status = 500
            code = 3001
            message = str(error)

    return {'success': 0,
            'code': code,
            'message': message}, status