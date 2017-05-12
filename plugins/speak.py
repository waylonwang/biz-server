from datetime import datetime

from pytz import utc
from sqlalchemy import Integer, String

import db_control
from app_view import CVAdminModelView
from plugin import PluginsRegistry

__registry__ = cr = PluginsRegistry()

# Model----------------------------------------------------------------------------------------------------
db = db_control.get_db()


class Speak(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'speak'

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    botid = db.Column(String(20), nullable=False)
    target = db.Column(String(20), nullable=False)
    sender_id = db.Column(String(20), nullable=False)
    sender_name = db.Column(String(20), nullable=False)
    date = db.Column(String(20), nullable=False)
    time = db.Column(String(20), nullable=False)
    timemark = db.Column(Integer)
    message = db.Column(String(20), nullable=False)
    washed_text = db.Column(String(20), nullable=False)
    washed_chars = db.Column(Integer)


class SpeakWash(db.Model):
    __bind_key__ = 'score'
    __tablename__ = 'speak_wash'

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    botid = db.Column(String(20), nullable=False)
    rule = db.Column(String(200), nullable=False)
    replace = db.Column(String(200), nullable=False)
    status = db.Column(Integer)
    createtime = db.Column(Integer, nullable=False)
    updatetime = db.Column(Integer, nullable=False, default=int(datetime.now(tz=utc).timestamp()))
    remark = db.Column(String(255), nullable=True)


class SpeakCount(db.Model):
    __bind_key__ = 'plugins'
    __tablename__ = 'speak_count'

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    botid = db.Column(String(20), nullable=False)
    target = db.Column(String(20), nullable=False)
    sender_id = db.Column(String(20), nullable=False)
    sender_name = db.Column(String(20), nullable=False)
    date = db.Column(String(20), nullable=False)
    message_count = db.Column(Integer)
    vaild_count = db.Column(Integer)


db.create_all()


@cr.model('10-Speak')
def get_Speak_model():
    return Speak


@cr.model('73-SpeakWash')
def get_SpeakWash_model():
    return SpeakWash


@cr.model('40-SpeakCount')
def get_SpeakCount_model():
    return SpeakCount


# View-----------------------------------------------------------------------------------------------------
class SpeakView(CVAdminModelView):
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 100
    column_filters = ('target', 'sender_id', 'sender_name', 'date', 'washed_chars')
    column_list = (
        'botid', 'target', 'sender_id', 'sender_name', 'date', 'time', 'message', 'washed_text', 'washed_chars')
    column_searchable_list = ('sender_name', 'message')
    column_labels = dict(botid='机器人ID', target='目标',
                         sender_id='发送者QQ', sender_name='发送者名称',
                         date='日期', time='时间',
                         message='消息原文', washed_text='有效消息内容', washed_chars='有效消息字数')
    # column_formatters = dict(date=lambda v, c, m, p: datetime.fromtimestamp(m.createtime).strftime('%Y-%m-%d'),
    #                          time=lambda v, c, m, p: datetime.fromtimestamp(m.updatetime).strftime('%Y-%m-%d'))
    column_formatters = dict(target=lambda v, c, m, p: _format_target(m.target),
                             sender_name=lambda v, c, m, p: str(m.sender_name)[0:10] + '...' if len(
                                 str(m.sender_name)) > 10 else str(m.sender_name)[0:10],
                             message=lambda v, c, m, p: str(m.message)[0:10] + '...' if len(
                                 str(m.message)) > 10 else str(m.message)[0:10],
                             washed_text=lambda v, c, m, p: str(m.washed_text)[0:10] + '...' if len(
                                 str(m.washed_text)) > 10 else str(m.washed_text)[0:10])

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '消息记录')

    def get_query(self):
        from flask_login import current_user
        if current_user.username != 'admin':
            return super(SpeakView, self).get_query().filter(self.model.botid == current_user.username)
        else:
            return super(SpeakView, self).get_query()

    def get_count_query(self):
        from flask_login import current_user
        from flask_admin.contrib.sqla.view import func
        if current_user.username != 'admin':
            return self.session.query(func.count('*')).filter(self.model.botid == current_user.username)
        else:
            return super(SpeakView, self).get_count_query()


class SpeakWashView(CVAdminModelView):
    column_filters = ('status',)
    column_labels = dict(id='规则ID', botid='机器人ID', rule='匹配规则', replace='清洗结果', status='状态',
                         createtime='创建时间', updatetime='更新时间', remark='备注')
    column_formatters = dict(status=lambda v, c, m, p: '启用' if m.status == 1 else '禁用',
                             createtime=lambda v, c, m, p: datetime.fromtimestamp(m.createtime).strftime('%Y-%m-%d'),
                             updatetime=lambda v, c, m, p: datetime.fromtimestamp(m.updatetime).strftime('%Y-%m-%d'))

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '发言清洗', '机器人设置')

    def get_query(self):
        from flask_login import current_user
        if current_user.username != 'admin':
            return super(SpeakWashView, self).get_query().filter(self.model.botid == current_user.username)
        else:
            return super(SpeakWashView, self).get_query()

    def get_count_query(self):
        from flask_login import current_user
        from flask_admin.contrib.sqla.view import func
        if current_user.username != 'admin':
            return self.session.query(func.count('*')).filter(self.model.botid == current_user.username)
        else:
            return super(SpeakWashView, self).get_count_query()


class SpeakCountView(CVAdminModelView):
    column_filters = ('sender_id', 'sender_name', 'date', 'message_count', 'vaild_count')
    column_list = ('botid', 'target', 'sender_id', 'sender_name', 'date', 'message_count', 'vaild_count')
    column_labels = dict(botid='机器人ID', target='目标', sender_id='发送者QQ', sender_name='发送者名称',
                         date='日期', message_count='消息总数', vaild_count='有效消息总数')
    column_formatters = dict(
        sender_name=lambda v, c, m, p: str(m.sender_name)[0:10] + '...' if len(str(m.sender_name)) > 10 else str(
            m.sender_name)[0:10],
        date=lambda v, c, m, p: datetime.fromtimestamp(m.createtime).strftime('%Y-%m-%d'))

    def __init__(self, model, session):
        CVAdminModelView.__init__(self, model, session, '发言统计', '统计分析')

    def get_query(self):
        from flask_login import current_user
        if current_user.username != 'admin':
            return super(SpeakCountView, self).get_query().filter(self.model.botid == current_user.username)
        else:
            return super(SpeakCountView, self).get_query()

    def get_count_query(self):
        from flask_login import current_user
        from flask_admin.contrib.sqla.view import func
        if current_user.username != 'admin':
            return self.session.query(func.count('*')).filter(self.model.botid == current_user.username)
        else:
            return super(SpeakCountView, self).get_count_query()


@cr.view('10-Speak')
def get_Speak_view():
    return SpeakView


@cr.view('73-SpeakWash')
def get_SpeakWash_view():
    return SpeakWashView


@cr.view('40-SpeakCount')
def get_SpeakCount_view():
    return SpeakCountView


def _format_target(text):
    return text.replace('g#', '群:').replace('d#', '组:').replace('p#', '单聊:')


# Control--------------------------------------------------------------------------------------------------
