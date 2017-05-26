import random
import string
from datetime import datetime

import pytz


def get_tz() -> pytz:
    return pytz.timezone(pytz.country_timezones('cn')[0])


def get_now() -> datetime:
    return datetime.now(get_tz())


def display_datetime(dt: datetime, hastime: bool = True) -> str:
    now = datetime.now()
    days = (now - dt).days
    time = '%H:%M' if hastime else ''
    space = ' ' if hastime else ''
    if days < 3:
        if now.day == dt.day:
            return dt.strftime('今天' + time)
        elif now.day == dt.day + 1:
            return dt.strftime('昨天' + time)
    elif now.year == dt.year:
        return dt.strftime('%m-%d' + space + time)
    else:
        return dt.strftime('%Y-%m-%d' + space + time)


def get_botname(botid: str) -> str:
    from common.bot import Bot
    return Bot.find(botid).name if Bot.find(botid) is not None else ''


def generate_key(len: int = 32, lowercase: bool = True, uppercase: bool = True, digits: bool = True) -> str:
    random.seed()
    chars = ''
    if lowercase: chars += string.ascii_lowercase
    if uppercase: chars += string.ascii_uppercase
    if digits: chars += string.digits
    return ''.join([random.choice(chars) for _ in range(len)])


def get_target_prefix(name: str) -> str:
    return {'group': 'g', 'discuzz': 'd', 'private': 'p'}.get(name, name)


def get_target_type_choice() -> list:
    return [('g', '群'), ('d', '组'), ('p', '单聊')]


def get_yesno_choice() -> list:
    return [('0', '否'), ('1', '是')]


def get_acttype_choice() -> list:
    return [('outgo', '支出'), ('income', '收入')]


def get_target_value(type: str, account: str) -> str:
    return get_target_prefix(type) + '#' + account


def get_target_display(target: str) -> str:
    return target.replace(target[0:2], {'g': '群', 'd': '组', 'p': '单聊'}.get(target[0:1], target) + ':')


def get_yesno_display(choice: int) -> str:
    return {0: '否', 1: '是'}.get(choice, '')


def get_acttype_display(type: str) -> str:
    return {'outgo': '支出', 'income': '收入'}.get(type, type)


def get_omit_display(text: str, length: int = 10) -> str:
    if text is not None:
        return text[0:length] + '...' if len(text) > length else text[0:length]
    else:
        return ''
    # return text.rjust(10,'.')