import smtplib
from email.mime.text import MIMEText
from email.header import Header

def send_email(subject: str,
               text: str,
               receivers=['2252286805@qq.com'],
               sender='944295661@qq.com'):
    # 邮件主题和内容
    # 邮件发送者和接收者
    # receiver = '2252286805@qq.com'
    # 用于登录SMTP服务器的信息
    username = '944295661@qq.com'
    # 登陆qq邮箱，在设置-账户-STMP位置生成16位授权码
    password = 'vdfvyafzezrebdgc'

    # 创建邮件对象
    message = MIMEText(text, 'plain', 'utf-8')
    message['From'] = Header(sender)
    message['To'] = Header(','.join(receivers), 'utf-8')
    message['Subject'] = Header(subject, 'utf-8')

    # SMTP服务器信息
    smtp_server = 'smtp.qq.com'
    port = 465
    
    # 发送邮件
    server = smtplib.SMTP_SSL(smtp_server, port)
    server.login(username, password)
    server.sendmail(sender, receivers, message.as_string())
    server.quit()
