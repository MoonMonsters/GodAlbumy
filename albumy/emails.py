# -*- coding: utf-8 -*-
"""
后台发送邮件模块
"""
from threading import Thread

from flask import current_app, render_template
from flask_mail import Message

from albumy.extensions import mail


def _send_async_mail(app, message):
	# 需要在flask环境中发送邮件，使用app.app_context可以使用该环境
	with app.app_context():
		mail.send(message)


def send_mail(to, subject, template, **kwargs):
	# 构造Message实例对象
	message = Message(current_app.config['ALBUMY_MAIL_SUBJECT_PREFIX'] + subject, recipients=[to])
	# 普通文本内容
	message.body = render_template(template + '.txt', **kwargs)
	# HTML格式的内容
	message.html = render_template(template + '.html', **kwargs)
	# 使用current_app._get_current_object()可以获取Flask对象
	app = current_app._get_current_object()
	# 在子线程中发送邮件
	thr = Thread(target=_send_async_mail, args=[app, message])
	thr.start()
	return thr


def send_confirm_email(user, token, to=None):
	"""
	发送验证邮箱的邮件
	:param user: 用户
	:param token: token值
	:param to: 被发送对象
	"""
	send_mail(subject='邮箱验证', to=to or user.email, template='emails/confirm', user=user, token=token)


def send_reset_password_email(user, token):
	"""
	发送重设密码的邮件
	"""
	send_mail(subject='密码重设', to=user.email, template='emails/reset_password', user=user, token=token)
