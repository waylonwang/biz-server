# import os
# import sqlite3
# from datetime import datetime
#
# import pytz
#
# from command import CommandRegistry
# from plugins import core
# from config import config
# from interactive import *
# from little_shit import get_db_dir, get_source, get_target, check_target
#
# __registry__ = cr = CommandRegistry()
#
# def _open_db_conn():
#     conn = sqlite3.connect(os.path.join(get_db_dir(), 'plugins.sqlite'))
#     conn.execute("""CREATE TABLE IF NOT EXISTS speak_apply (
#         id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
#         target TEXT NOT NULL,
#         uid TEXT NOT NULL,
#         date TEXT NOT NULL,
#         time INTEGER NOT NULL,
#         hasrecord INTEGER NOT NULL
#         )""")
#     conn.execute("""CREATE TABLE IF NOT EXISTS speak_record (
#         id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
#         target TEXT NOT NULL,
#         uid TEXT NOT NULL,
#         date TEXT NOT NULL,
#         count INTEGER NOT NULL
#         )""")
#     conn.execute("""CREATE TABLE IF NOT EXISTS point_apply (
#         id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
#         target TEXT NOT NULL,
#         target_uid TEXT NOT NULL,
#         apply_uid TEXT NOT NULL,
#         date TEXT NOT NULL,
#         time INTEGER NOT NULL,
#         point INTEGER NOT NULL,
#         hasrecord INTEGER NOT NULL
#         )""")
#     conn.execute("""CREATE TABLE IF NOT EXISTS confirm_code (
#         id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
#         link_type TEXT NOT NULL,
#         link_id INTEGER NOT NULL,
#         target_uid TEXT NOT NULL,
#         date TEXT NOT NULL,
#         time INTEGER NOT NULL,
#         code INTEGER NOT NULL,
#         hasconfirm INTEGER NOT NULL
#         )""")
#     conn.commit()
#     return conn
#
#
# _cmd_take = 'note.take'
# _cmd_remove = 'note.remove'
#
#
# @cr.register('统计发言')
# @check_target
# def speak_apply(args_text, ctx_msg):
#     source = get_source(ctx_msg)
#
#     conn = _open_db_conn()
#     date_text = datetime.now(tz=pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d')
#     time_unix = int(datetime.now(tz=pytz.timezone('Asia/Shanghai')).timestamp())
#     daily_limit = config.get('score_daily_speak_apply_limit')
#     try:
#         cursor = conn.execute('SELECT count(id) FROM speak_apply WHERE target=? and uid = ? and date = ?',
#                               (get_target(ctx_msg),ctx_msg.get('sender_id',''),date_text))
#         today_cnt = cursor.fetchone()[0]
#         if today_cnt == daily_limit - 1 :
#             core.echo('[CQ:at,qq='+ ctx_msg.get('sender_id')+'] 温馨提醒：你今天还剩一次统计发言的机会', ctx_msg)
#         elif today_cnt > daily_limit :
#             core.echo('[CQ:at,qq=' + ctx_msg.get('sender_id') + '] 你今天可统计发言的次数已经用完', ctx_msg)
#     except :
#         pass
#     finally:
#         try:
#             if today_cnt <= daily_limit :
#                 conn.execute(
#                     'INSERT INTO speak_apply (target, uid, date, time, hasrecord) VALUES (?, ?, ?, ?, 0)',
#                     (get_target(ctx_msg), ctx_msg.get('sender_id',''), date_text, time_unix)
#                 )
#                 conn.commit()
#                 core.echo('查询发言 @'+ ctx_msg.get('sender_name',''), ctx_msg)
#         except:
#             core.echo('[CQ:at,qq=' + ctx_msg.get('sender_id') + '] 对不起，程序出错了，暂时无法统计发言，请稍后再试！', ctx_msg)
#         finally:
#             conn.close()
#
#
# @cr.register('@.*今天有效发言数')
# @check_target
# def speak_record_save(args_text, ctx_msg):
#     conn = _open_db_conn()
#     target = get_target(ctx_msg)
#     cursor = conn.execute('SELECT id, dt, content FROM cmd_note WHERE target = ?', (target,))
#     rows = list(cursor)
#     conn.close()
#     if len(rows) == 0:
#         core.echo('还没有笔记哦～', ctx_msg)
#         return
#     for row in rows:
#         tz_china = pytz.timezone('Asia/Shanghai')
#         dt_raw = datetime.fromtimestamp(row[1], tz=pytz.utc)
#         core.echo('ID：' + str(row[0])
#                   + '\n时间：' + dt_raw.astimezone(tz_china).strftime('%Y.%m.%d %H:%M')
#                   + '\n内容：' + str(row[2]),
#                   ctx_msg)
#     core.echo('以上～', ctx_msg)
#
#
# @cr.register('报点')
# @check_target
# def point_apply(args_text, ctx_msg, allow_interactive=True):
#     source = get_source(ctx_msg)
#     if allow_interactive and (not args_text or has_session(source, _cmd_remove)):
#         # Be interactive
#         return _remove_interactively(args_text, ctx_msg, source)
#
#     try:
#         note_id = int(args_text)
#     except ValueError:
#         # Failed to cast
#         core.echo('你输入的 ID 格式不正确哦～应该是个数字才对～', ctx_msg)
#         return
#     conn = _open_db_conn()
#     target = get_target(ctx_msg)
#     cursor = conn.cursor()
#     cursor.execute('DELETE FROM cmd_note WHERE target = ? AND id = ?', (target, note_id))
#     if cursor.rowcount > 0:
#         core.echo('删除成功了～', ctx_msg)
#     else:
#         core.echo('没找到这个 ID 的笔记哦～', ctx_msg)
#     conn.commit()
#     conn.close()
#
#
# @cr.register('确认')
# @check_target
# def code_confirm(_, ctx_msg):
#     conn = _open_db_conn()
#     target = get_target(ctx_msg)
#     cursor = conn.cursor()
#     cursor.execute('DELETE FROM cmd_note WHERE target = ?', (target,))
#     if cursor.rowcount > 0:
#         core.echo('成功删除了所有的笔记，共 %s 条～' % cursor.rowcount, ctx_msg)
#     else:
#         core.echo('本来就没有笔记哦～', ctx_msg)
#     conn.commit()
#     conn.close()
#
#
# _state_machines = {}
#
# # 统计每天发言
# # 统计每周报点
#
# def _take_interactively(args_text, ctx_msg, source):
#     def wait_for_content(s, a, c):
#         core.echo('请发送你要记录的内容：', c)
#         s.state += 1
#
#     def save_content(s, a, c):
#         take(a, c, allow_interactive=False)
#         return True
#
#     if _cmd_take not in _state_machines:
#         _state_machines[_cmd_take] = (
#             wait_for_content,  # 0
#             save_content  # 1
#         )
#
#     sess = get_session(source, _cmd_take)
#     if _state_machines[_cmd_take][sess.state](sess, args_text, ctx_msg):
#         # Done
#         remove_session(source, _cmd_take)
#
#
# def _remove_interactively(args_text, ctx_msg, source):
#     def wait_for_note_id(s, a, c):
#         core.echo('请发送你要删除的笔记的 ID：', c)
#         s.state += 1
#
#     def remove_note(s, a, c):
#         remove(a, c, allow_interactive=False)
#         return True
#
#     if _cmd_remove not in _state_machines:
#         _state_machines[_cmd_remove] = (
#             wait_for_note_id,  # 0
#             remove_note  # 1
#         )
#
#     sess = get_session(source, _cmd_remove)
#     if _state_machines[_cmd_remove][sess.state](sess, args_text, ctx_msg):
#         # Done
#         remove_session(source, _cmd_remove)
