import requests
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import datetime
import time
import numpy as np
import logging
from logging.handlers import TimedRotatingFileHandler


def get_logger(with_console=True, with_file=False):
    formatter = '%(asctime)s.%(msecs)03d %(levelname)s %(filename)s:%(lineno)d: %(message)s'
    lg = logging.getLogger(__name__)
    lg.setLevel(level=logging.INFO)
    if with_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level=logging.INFO)
        console_handler.setFormatter(logging.Formatter(formatter))
        lg.addHandler(console_handler)
    if with_file:
        time_rotate_file = TimedRotatingFileHandler(filename='logs/taoli.log', when='D', interval=1, backupCount=90)
        time_rotate_file.setFormatter(logging.Formatter(formatter))
        time_rotate_file.setLevel(logging.INFO)
        time_rotate_file.namer = lambda name: name.replace(".log", "") + ".log"
        lg.addHandler(time_rotate_file)
    return lg


def wx_send(msg):
    webhook="http://in.qyapi.weixin.qq.com/cgi-bin/webhook/send"
    headers = {
        'Content-Type': 'application/json',
    }
    params = {
        'key': '5876d644-bcf5-40ae-a032-eda11e857e1d',
    }
    json_data = {
        'msgtype': 'text',
        'text': {
            'content': str(msg),
        },
    }
    requests.post(webhook, params=params, headers=headers, json=json_data)


def ts2dt(st:str, fmt='%Y-%m-%d %H:%M:%S'):
    # st: unix timestamp /ms
    # fromtimestamp 入参为秒
    dt = datetime.datetime.fromtimestamp(int(st)/1000)
    return dt.strftime(fmt)


def dt2ts(dt:str, fmt='%Y-%m-%d %H:%M:%S'):
    # dt: datetime str
    t = datetime.datetime.strptime(dt, fmt)
    return t.timestamp() * 1000


# 获取时间粒度的数字间隔（默认毫秒）
def get_interval(bar: str, MINUTE_BAR_INTERVAL=60000) -> float:
    '''
    :param bar: 时间粒度 1m 3m 5m 15m 1h 2h 4h 1d ...
    :param MINUTE_BAR_INTERVAL: 每分钟的数字间隔，默认毫秒
    '''
    bar_int = int(bar[0:-1].strip())
    suffix = bar[-1].lower()
    if suffix == 's':
        interval = int((MINUTE_BAR_INTERVAL / 60) * bar_int)
    elif suffix == 'm':
        interval = MINUTE_BAR_INTERVAL * bar_int
    elif suffix == 'h':
        interval = MINUTE_BAR_INTERVAL * 60 * bar_int
    elif suffix == 'd':
        interval = MINUTE_BAR_INTERVAL * 60 * 24 * bar_int
    elif suffix == 'w':
        interval = MINUTE_BAR_INTERVAL * 60 * 24 * 7 * bar_int
    else:
        raise ValueError(
            func='get_interval',
            bar=bar
        )
    return interval


# 预计历史K线的时间间隔
def predict_interval(candle: np.array) -> float:
    '''
    :param candle: 历史K线
    '''
    return np.min(np.diff(candle[:, 0]))


# 历史K线 根据num获取最佳的limit
def get_limit(num: int) -> int:
    return int(np.clip(num, 1, 1500))


def send_email(msg):
    # 邮件主题和内容
    subject = '此时套利数据'
    text = str(msg)
    
    # 邮件发送者和接收者
    sender = '944295661@qq.com'
    receiver = '2252286805@qq.com'
    # 用于登录SMTP服务器的信息
    username = '944295661@qq.com'
    # 登陆qq邮箱，在设置-账户-STMP位置生成16位授权码
    password = 'vdfvyafzezrebdgc'

    # 创建邮件对象
    message = MIMEText(text, 'plain', 'utf-8')
    message['From'] = Header(sender)
    message['To'] = Header(receiver, 'utf-8')
    message['Subject'] = Header(subject, 'utf-8')

    # SMTP服务器信息
    smtp_server = 'smtp.qq.com'
    port = 465
    
    # 发送邮件
    server = smtplib.SMTP_SSL(smtp_server, port)
    server.login(username, password)
    server.sendmail(sender, [receiver], message.as_string())
    server.quit()


if __name__ == '__main__':
    wx_send('123')
