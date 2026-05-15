import smtplib
from email.message import EmailMessage
def send_mail(to,body,subject):
    server=smtplib.SMTP_SSL('smtp.gmail.com',465)
    server.login('anusha@codegnan.com','gfzu jygl eyat aokg')
    msg=EmailMessage()
    msg['FROM']='anusha@codegnan.com'
    msg['TO']=to
    msg['SUBJECT']=subject
    msg.set_content(body)
    server.send_message(msg)
    server.close()