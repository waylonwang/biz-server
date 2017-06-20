'''
    统计服务接口
'''


def get_statistics_data(request):
    '''
        获取dashboard的统计数据
    :param request: HTTP请求对象l
    :return: 统计数据
    '''
    from datetime import timedelta

    from common.util import output_datetime, get_now

    if request.method == 'GET':
        type = request.args.get('type')
        botid = request.args.get('botid')
        target = request.args.get('target')
        days = request.args.get('days')
    elif request.method == 'POST':
        type = request.form.get('type')
        botid = request.form.get('botid')
        target = request.form.get('target')
        days = request.form.get('days')

    today = output_datetime(get_now(), True, False)
    if int(type) == 1:
        # 汇总数据
        return _get_counts(botid)
    elif int(type) == 2:
        # 查询发言统计
        if int(days) == 7 or int(days) == 30 or int(days) == 60:
            return _get_speak_statistics(botid,
                                         target,
                                         output_datetime(get_now() - timedelta(days = int(days)), True, False),
                                         today)
        else:
            return {'success': 0}
    elif int(type) == 3:
        # 重新计算发言统计
        return _do_speak_statistics(botid, target, today, today)
    elif int(type) == 4:
        # 发言排行榜
        if int(days) == 0 or int(days) == 1:
            # 0：查询今天
            # 1：查询昨天
            return _get_speak_tops(botid,
                                   target,
                                   output_datetime(get_now() - timedelta(days = int(days)), True, False),
                                   output_datetime(get_now() - timedelta(days = int(days)), True, False))
        elif int(days) == 7 or int(days) == 99999:
            # 7：查询7天内
            # 99999：查询全部
            return _get_speak_tops(botid,
                                   target,
                                   output_datetime(get_now() - timedelta(days = int(days)), True, False),
                                   today)
        else:
            return {'success': 0}
    else:
        return {'success': 0}


def _get_speak_statistics(botid, target, date_from, date_to):
    '''
        获取发言统计数据
    :param botid: 机器人ID
    :param target: 目标
    :param date_from: 开始日期
    :param date_to: 结束日期
    :return: 统计数据
    '''
    import math
    from common.util import target_prefix2name
    from plugins.speak import SpeakCount

    max_count = 0
    min_count = 0
    statistics_data = SpeakCount.statistics(botid,
                                            target_prefix2name(target.split('#')[0]),
                                            target.split('#')[1],
                                            date_from,
                                            date_to).fetchall()

    for r in statistics_data:
        max_count = max(max_count, int(r.message_count))
        min_count = min(min_count if min_count != 0 else max_count, int(r.vaild_count))

    return {'success': 1,
            'data': {
                'botid': botid,
                'target': target,
                'max_speaks': math.ceil(max_count / 100) * 100,
                'min_speaks': math.floor(min_count / 100) * 100,
                'statistics_data': [
                    {'date': r.date,
                     'message_count': r.message_count,
                     'vaild_count': r.vaild_count} for r in statistics_data]}
            }


def _do_speak_statistics(botid, target, date_from, date_to):
    '''
        重新计算发言统计
    :param botid: 机器人ID
    :param target: 目标
    :param date_from: 开始日期
    :param date_to: 结束日期
    :return: 是否成功
    '''
    from plugins.speak import SpeakCount
    from common.util import target_prefix2name

    if SpeakCount.do(botid,
                     target_prefix2name(target.split('#')[0]),
                     target.split('#')[1],
                     date_from,
                     date_to):
        return {'success': 1}
    else:
        return {'success': 0}


def _get_speak_tops(botid, target, date_from, date_to):
    '''
        获取发言排行榜
    :param botid: 机器人ID
    :param target: 目标
    :param date_from: 开始日期
    :param date_to: 结束日期
    :return: 统计数据 
    '''
    from plugins.speak import Speak
    from common.util import target_prefix2name, get_CQ_display

    records = Speak.get_top(botid,
                            target_prefix2name(target.split('#')[0]),
                            target.split('#')[1],
                            date_from,
                            date_to)
    top_data = [{'name': get_CQ_display(r.sender_name), 'id': r.sender_id, 'count': r.cnt} for r in records]

    return {'success': 1,
            'data': {
                'botid': botid,
                'target': target,
                'statistics_data': [
                    {'name': get_CQ_display(r.sender_name),
                     'id': r.sender_id,
                     'count': r.cnt} for r in records]}
            }


def _get_counts(botid):
    from plugins.setting import TargetRule

    from common import login
    from common.util import output_datetime, get_now
    targets = TargetRule.find_allow_by_user(login.current_user.username)

    speak_today_count = 0
    sign_today_count = 0
    point_today_total = 0
    score_today_total = 0

    today = '2017-05-30'  # output_datetime(get_now(), True, False)

    for target in targets:
        speak_today_count += _get_speak_today_count(botid, target, today, today)
        sign_today_count += _get_sign_today_count(botid, target, today, today)
        point_today_total += _get_point_today_total(botid, target, today, today)
        score_today_total += _get_score_today_total(botid, target, today, today)
    return {'success': 1,
            'data': {
                'statistics_data':
                    {'speak_today_count': speak_today_count,
                     'sign_today_count': sign_today_count,
                     'point_today_total': point_today_total,
                     'score_today_total': score_today_total}}

            }


def _get_speak_today_count(botid, target, date_from, date_to):
    from plugins.speak import Speak
    from common.util import target_prefix2name

    speak_today = Speak.get_count(target.botid, target_prefix2name(target.target.split('#')[0]),
                                  target.target.split('#')[1], date_from, date_to)
    return speak_today.cnt_full if speak_today.cnt_full is not None else 0


def _get_score_today_total(botid, target, date_from, date_to):
    from plugins.score import ScoreRecord
    from common.util import target_prefix2name

    score_today = ScoreRecord.get_flow(target.botid, target_prefix2name(target.target.split('#')[0]),
                                       target.target.split('#')[1], date_from, date_to)
    return score_today.total if score_today.total is not None else 0


def _get_point_today_total(botid, target, date_from, date_to):
    from plugins.point import Point
    from common.util import target_prefix2name

    point_today = Point.get_total(target.botid, target_prefix2name(target.target.split('#')[0]),
                                  target.target.split('#')[1], date_from, date_to)
    return point_today.total_success if point_today.total_success is not None else 0


def _get_sign_today_count(botid, target, date_from, date_to):
    from plugins.sign import Sign
    from common.util import target_prefix2name

    sign_today = Sign.get_count(target.botid, target_prefix2name(target.target.split('#')[0]),
                                target.target.split('#')[1], date_from, date_to)
    return sign_today.cnt if sign_today.cnt is not None else 0