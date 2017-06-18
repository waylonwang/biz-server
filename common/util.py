import random
import re
import string
from datetime import datetime, date, time

import pytz
from markupsafe import Markup


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
    if now.year == dt.year:
        return dt.strftime('%m-%d' + space + time)
    else:
        return dt.strftime('%Y-%m-%d' + space + time)


def output_datetime(dt, hasdate: bool = True, hastime: bool = True) -> str:
    date_pattern = '%Y-%m-%d' if hasdate else ''
    time_pattern = '%H:%M' if hastime else ''
    space = ' ' if hastime else ''
    if isinstance(dt, datetime):
        return dt.strftime(date_pattern + space + time_pattern)
    elif isinstance(dt, date):
        return dt.strftime('%Y-%m-%d')
    elif isinstance(dt, time):
        return dt.strftime('%H:%M')
    else:
        return str(dt)


def get_botname(botid: str) -> str:
    from common.bot import Bot
    return Bot.find(botid).name if Bot.find(botid) is not None else '[已删除]' + botid


def generate_key(len: int = 32, lowercase: bool = True, uppercase: bool = True, digits: bool = True) -> str:
    random.seed()
    chars = ''
    if lowercase: chars += string.ascii_lowercase
    if uppercase: chars += string.ascii_uppercase
    if digits: chars += string.digits
    return ''.join([random.choice(chars) for _ in range(len)])


def target_name2prefix(name: str) -> str:
    return {'group': 'g', 'discuzz': 'd', 'private': 'p'}.get(name, name)


def target_name2display(name: str) -> str:
    return {'group': '群', 'discuzz': '组', 'private': '单聊'}.get(name, name)


def target_prefix2name(name: str) -> str:
    return {'g': 'group', 'd': 'discuzz', 'p': 'private'}.get(name, name)


def target_prefix2display(name: str) -> str:
    return {'g': '群', 'd': '组', 'p': '单聊'}.get(name, name)


def target_display2name(name: str) -> str:
    return {'群': 'group', '组': 'discuzz', '单聊': 'private'}.get(name, name)


def target_display2prefix(name: str) -> str:
    return {'群': 'g', '组': 'd', '单聊': 'p'}.get(name, name)


def get_target_type_choice() -> list:
    return [('g', '群'), ('d', '组'), ('p', '单聊')]


def get_yesno_choice() -> list:
    return [('0', '否'), ('1', '是')]


def get_acttype_choice() -> list:
    return [('outgo', '支出'), ('income', '收入'), ('transfer', '转账')]


def get_target_composevalue(type: str, account: str) -> str:
    return target_name2prefix(type) + '#' + account.strip()


def recover_target_value(target_display: str) -> str:
    return get_target_composevalue(target_display2name(target_display.split(' : ')[0]),
                                   target_display.split(':')[1])


def get_target_display(target: str) -> str:
    return target.replace(target[0:2], target_prefix2display(target[0:1]) + ' : ')


def get_yesno_display(choice: int) -> str:
    return {0: '否', 1: '是'}.get(choice, '')


def get_acttype_display(type: str) -> str:
    return {'outgo': '支出', 'income': '收入', 'transfer': '转账'}.get(type, type)


def get_transtype_display(type: str, isoutgo: bool) -> str:
    if type == 'transfer': type += '_' + 'outgo' if isoutgo else '_' + 'income'
    return {'outgo': '支出', 'income': '收入', 'transfer_outgo': '转出', 'transfer_income': '转入'}.get(type, type)


def get_omit_display(text: str, length: int = 20) -> str:
    def get_plus_len(text: str, length: int) -> int:
        def _len_list(text: str) -> list:
            # def len_zh(text: str) -> int:
            #     # 中文 [\u4e00-\u9fa5]
            #     # 非ASCII [^\x00-\xff]
            #     temp = re.findall('[^\x00-\xff]+', text)
            #     count = 0
            #     for i in temp:
            #         count += len(i)
            #     return (count)
            #
            # def len_nzh(text: str) -> int:
            #     temp = re.findall('[\x00-\xff]+', text)
            #     count = 0
            #     for i in temp:
            #         count += len(i)
            #     return (count)
            #
            # def len_plus(text: str) -> int:
            #     return len_nzh(text) + len_zh(text) * 2
            def _len(text: str) -> int:
                # 中文 [\u4e00-\u9fa5]
                # 非ASCII [^\x00-\xff]
                return len(re.sub(r'[^\x00-\xff]', 'aa', text))

            dlist = list(text)
            return [_len(t) for t in dlist]

        lenlist = _len_list(text)
        cnt = 0
        total = 0
        for i in lenlist:
            total += i
            if total > length: return cnt
            cnt += 1
        return cnt

    if text is not None:
        omit_length = get_plus_len(text, length)
        return text[0:omit_length] + '...' if omit_length < len(text) else text
    else:
        return ''


def get_list_by_botassign(model_class, view_class, view_object):
    from flask_login import current_user
    if not current_user.is_admin():
        from common.bot import BotAssign
        botids = tuple([r.botid for r in BotAssign.find_by_user(current_user.username)])
        return super(view_class, view_object).get_query().filter(model_class.botid.in_(botids))
    else:
        return super(view_class, view_object).get_query()


def get_list_count_by_botassign(model_class, view_class, view_object):
    from flask_login import current_user
    from flask_admin.contrib.sqla.view import func
    if not current_user.is_admin():
        from common.bot import BotAssign
        botids = tuple([r.botid for r in BotAssign.find_by_user(current_user.username)])
        return view_object.session.query(func.count(1)).filter(model_class.botid.in_(botids))
    else:
        return super(view_class, view_object).get_count_query()


def get_list_by_scoreaccount(model_class, view_class, view_object):
    from flask_login import current_user
    if not current_user.is_admin():
        from plugins.score import ScoreAccount
        accounts = tuple([r.name for r in ScoreAccount.find_by_user(current_user.username)])
        return super(view_class, view_object).get_query().filter(model_class.account.in_(accounts))
    else:
        return super(view_class, view_object).get_query()


def get_list_count_by_scoreaccount(model_class, view_class, view_object):
    from flask_login import current_user
    from flask_admin.contrib.sqla.view import func
    if not current_user.is_admin():
        from plugins.score import ScoreAccount
        accounts = tuple([r.name for r in ScoreAccount.find_by_user(current_user.username)])
        return view_object.session.query(func.count(1)).filter(model_class.account.in_(accounts))
    else:
        return super(view_class, view_object).get_count_query()


def get_CQ_display(text: str):
    def display_emoji(text: str):
        def replace_text(matched):
            if matched.group("id") != None:
                return chr(int(matched.group("id")))
            else:
                return ''

        return re.sub(r'\[CQ:emoji,id=(?P<id>[^\]]*)\]', replace_text, text)

    def display_at(text: str):
        return re.sub(r'\[CQ:at,qq=(?P<id>[^\]]*)\]', '<div class="CQ_at" >@' + r'\g<id>' + '</div>', text)

    def display_sign(text: str):
        return re.sub(r'\[CQ:sign[^\]]*\]',
                      '<span class="CQ_icon" style="background:darkslateblue;"><i class="fa fa-flag-checkered"></i></span>',
                      text)

    def display_bface(text: str):
        return re.sub(r'\[CQ:bface[^\]]*\](?:\[[^\]]*\])*',
                      '<span class="CQ_icon" style="background:gold;"><i class="fa fa-smile-o"></i></span>', text)

    def display_face(text: str):
        def replace_text(matched):
            if matched.group("id") != None:
                id = matched.group("id")
                left = int(id) % 15 * 20
                top = int(id) // 15 * 20
                return '<div class="CQ_face" style="background: url(\'/static/images/qqface20.png\') -' + str(
                    left) + 'px -' + str(top) + 'px no-repeat;"></div>'
            else:
                return '<span class="CQ_icon"><i class="fa fa-smile-o"></i></span>'

        return re.sub(r'\[CQ:face,id=(?P<id>[^\]]*)\]', replace_text, text)

    def display_sface(text: str):
        return re.sub(r'\[CQ:sface,id=[^\]]*\]',
                      '<span class="CQ_icon" style="background:salmon;"><i class="fa fa-smile-o"></i></span>', text)

    def display_share(text: str):
        return re.sub(r'\[CQ:share,[^\]]*\]]',
                      '<span class="CQ_icon" style="background:dodgerblue;"><i class="fa fa-link"></i></span>', text)

    def display_image(text: str):
        return re.sub(r'\[CQ:image,file=[^\]]*\]',
                      '<span class="CQ_icon"style="background:lightseagreen;"><i class="glyphicon glyphicon-picture"></i></span>',
                      text)

    def display_record(text: str):
        return re.sub(r'\[CQ:record,file=[^\]]*\]',
                      '<span class="CQ_icon" style="background:mediumvioletred;"><i class="glyphicon glyphicon-volume-up"></i></span>',
                      text)

    def display_music(text: str):
        return re.sub(r'\[CQ:music,type=[^\]]*\]',
                      '<span class="CQ_icon" style="background:brown;"><i class="glyphicon glyphicon-music"></i></span>',
                      text)

    text = display_emoji(text)
    text = display_at(text)
    text = display_sign(text)
    text = display_bface(text)
    text = display_sface(text)
    text = display_face(text)
    text = display_share(text)
    text = display_image(text)
    text = display_record(text)
    text = display_music(text)
    return Markup(text)