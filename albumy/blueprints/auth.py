# -*- coding: utf-8 -*-
"""
用户验证模块
"""
from flask import render_template, flash, redirect, url_for, Blueprint,request
from flask_login import login_user, logout_user, login_required, current_user, login_fresh, confirm_login

from albumy.emails import send_confirm_email, send_reset_password_email
from albumy.extensions import db
from albumy.forms.auth import LoginForm, RegisterForm, ForgetPasswordForm, ResetPasswordForm
from albumy.models import User
from albumy.settings import Operations
from albumy.utils import generate_token, validate_token, redirect_back,logger

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
	"""
	用户登录
	"""
	logger.info('url = ' + str(request.url))
	# 如果用户已经登录，就不再需要登录，直接返回主页
	if current_user.is_authenticated:
		return redirect(url_for('main.index'))

	form = LoginForm()
	# 登录
	if form.validate_on_submit():
		# 将email转成小写然后取用户数据，注册时也转成了小写
		user = User.query.filter_by(email=form.email.data.lower()).first()
		# 用户不存在或者验证密码错误
		# 取出用户数据后，调用validate_password来判断密码是否匹配，密码都是加密的
		if user is not None and user.validate_password(form.password.data):
			# login_user是flask-login库的，用来保存用户信息
			if login_user(user, form.remember_me.data):
				flash('登录成功！', 'info')
				return redirect_back()
			else:
				flash('你的账号已被禁止登录！', 'warning')
				return redirect(url_for('main.index'))
		flash('错误的邮箱或者密码，请确认后再登录！', 'warning')
	return render_template('auth/login.html', form=form)


@auth_bp.route('/re-authenticate', methods=['GET', 'POST'])
@login_required
def re_authenticate():
	"""
	重新认证
	"""
	logger.info('url = ' + str(request.url))
	# 刷新
	if login_fresh():
		return redirect(url_for('main.index'))

	form = LoginForm()
	if form.validate_on_submit() and current_user.validate_password(form.password.data):
		confirm_login()
		return redirect_back()
	return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
	"""
	注销
	"""
	logger.info('url = ' + str(request.url))
	# 清空用户信息
	logout_user()
	flash('注销成功！', 'info')
	return redirect(url_for('main.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
	"""
	注册
	"""
	logger.info('url = ' + str(request.url))
	# 如果用户已经登录，则直接返回主页
	if current_user.is_authenticated:
		return redirect(url_for('main.index'))

	form = RegisterForm()
	if form.validate_on_submit():
		name = form.name.data
		# 将邮箱转成小写，避免验证出问题
		email = form.email.data.lower()
		username = form.username.data
		password = form.password.data
		user = User(name=name, email=email, username=username)
		user.set_password(password)
		db.session.add(user)
		db.session.commit()
		# 获取token
		token = generate_token(user=user, operation='confirm')
		# 发送验证邮箱
		send_confirm_email(user=user, token=token)
		flash('邮件已发送，请登录邮箱验证！', 'info')
		return redirect(url_for('.login'))
	return render_template('auth/register.html', form=form)


@auth_bp.route('/confirm/<token>')
@login_required
def confirm(token):
	"""
	验证邮箱
	:param token: register中通过邮件发送的token，有时间限制
	"""
	logger.info('url = ' + str(request.url))
	# 如果已经验证通过，不需要重复验证
	if current_user.confirmed:
		return redirect(url_for('main.index'))

	# 验证token
	if validate_token(user=current_user, token=token, operation=Operations.CONFIRM):
		flash('验证通过！', 'success')
		return redirect(url_for('main.index'))
	else:
		flash('无效或过期的token！', 'danger')
		# 重新发送邮件
		return redirect(url_for('.resend_confirm_email'))


@auth_bp.route('/resend-confirm-email')
@login_required
def resend_confirm_email():
	"""
	重新发送验证邮件
	"""
	logger.info('url = ' + str(request.url))
	if current_user.confirmed:
		return redirect(url_for('main.index'))

	token = generate_token(user=current_user, operation=Operations.CONFIRM)
	send_confirm_email(user=current_user, token=token)
	flash('新邮件已发送，请登录邮箱验证！', 'info')
	return redirect(url_for('main.index'))


@auth_bp.route('/forget-password', methods=['GET', 'POST'])
def forget_password():
	"""
	忘记密码
	"""
	logger.info('url = ' + str(request.url))
	# 如果已经登录，则跳转到主页
	# 该功能只适用于登录记不起密码时使用
	if current_user.is_authenticated:
		return redirect(url_for('main.index'))

	form = ForgetPasswordForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data.lower()).first()
		if user:
			token = generate_token(user=user, operation=Operations.RESET_PASSWORD)
			# 重置密码
			send_reset_password_email(user=user, token=token)
			flash('邮件已发送，请登录邮箱点击链接重置密码！', 'info')
			return redirect(url_for('.login'))
		flash('无效邮箱，请重新输入！', 'warning')
		return redirect(url_for('.forget_password'))
	return render_template('auth/reset_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
	"""
	重设密码
	:param token: 点击邮件中的链接携带的token
	"""
	logger.info('url = ' + str(request.url))
	# 如果用户已经登录，不需要重设密码
	if current_user.is_authenticated:
		return redirect(url_for('main.index'))

	form = ResetPasswordForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data.lower()).first()
		# 用户不存在
		if user is None:
			return redirect(url_for('main.index'))
		# 验证token的有效性
		if validate_token(user=user, token=token, operation=Operations.RESET_PASSWORD,
						  new_password=form.password.data):
			flash('密码重置成功！', 'success')
			return redirect(url_for('.login'))
		else:
			flash('无效或过期链接！', 'danger')
			# 跳转到忘记密码页面
			return redirect(url_for('.forget_password'))
	# 重设密码
	return render_template('auth/reset_password.html', form=form)
