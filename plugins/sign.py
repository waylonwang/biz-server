# from command import CommandRegistry, split_arguments
# from plugins import core
# from plugins.admin import _check_admin_group
# from plugins.db import _open_db_conn
# from little_shit import get_target, check_target
#
# __registry__ = cr = CommandRegistry()
# __target_prefix = {'group': 'group_id', 'discuss': 'discuss_id', 'private': 'sender_id'}
#
# @cr.register('签到')
# @split_arguments(maxsplit=1)
# @check_target
# def sign(_, ctx_msg, argv=None):
#     # conn = _open_db_conn()
#     # cursor = conn.execute("SELECT SUM(1) AS fullcount ,"
#     #                       "SUM("
#     #                       " CASE WHEN CAST(charcount AS INT) >= ("
#     #                       "     SELECT CAST(param_value AS INT) "
#     #                       "     FROM sys_params WHERE param_name='baseline') "
#     #                       " THEN 1 ELSE 0 END) AS validcount "
#     #                       "FROM speak WHERE target=? AND (sender_id=? OR sender_name=?) AND date=? ",
#     #                       (group, user, user, date))
#     # result = cursor.fetchone()
#     # conn.close()
#     # if result[0] == None:
#     #     result = (0, 0)
#     pass
