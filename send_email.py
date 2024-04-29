import smtplib
from email.mime.text import MIMEText
from email.header import Header
 
# 邮件发送者和接收者
sender = 'xxx@qq.com'
receiver = '2252286805@qq.com'
 
# 邮件主题和内容
subject = '邮件主题-测试'
text = '邮件内容-测试'
 
# SMTP服务器信息
smtp_server = 'smtp.qq.com'
port = 465

# 用于登录SMTP服务器的信息
username = 'xxx@qq.com'
# 登陆qq邮箱，在设置-账户-STMP位置生成16位授权码
password = ''

# 创建邮件对象
message = MIMEText(text, 'plain', 'utf-8')
message['From'] = Header(sender)
message['To'] = Header(receiver, 'utf-8')
message['Subject'] = Header(subject, 'utf-8')
 
# 发送邮件
server = smtplib.SMTP_SSL(smtp_server, port)
server.login(username, password)
server.sendmail(sender, [receiver], message.as_string())
server.quit()