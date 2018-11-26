# -*- coding: utf-8 -*-
from functools import wraps

from flask import Markup, flash, url_for, redirect, abort
from flask_login import current_user


def confirm_required(func):
	"""
	当访问视图时，判断用户是否已经验证过邮箱
	:param func: 视图函数
	"""

	@wraps(func)
	def decorated_function(*args, **kwargs):
		# 如果用户没有验证邮箱
		if not current_user.confirmed:
			# 重新发送邮件
			message = Markup(
				'请先验证您的邮箱。'
				'没有收到邮件？'
				'<a class="alert-link" href="%s">重新发送</a>' %
				url_for('auth.resend_confirm_email'))
			flash(message, 'warning')
			# 跳到主页面
			return redirect(url_for('main.index'))
		return func(*args, **kwargs)

	return decorated_function


def permission_required(permission_name):
	"""
	某些视图函数需要用户具有权限才能访问
	该装饰器就是用来判断用户是否具有访问视图函数的权限的
	:param permission_name: 权限名称
	"""

	def decorator(func):
		@wraps(func)
		def decorated_function(*args, **kwargs):
			# 如果用户没有权限，则抛出403错误
			if not current_user.can(permission_name):
				abort(403)
			# 否则正常执行
			return func(*args, **kwargs)

		return decorated_function

	return decorator


def admin_required(func):
	"""
	需要管理员权限才能访问
	:param func: 函数
	"""
	return permission_required('ADMINISTER')(func)
