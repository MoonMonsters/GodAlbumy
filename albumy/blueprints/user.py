# -*- coding: utf-8 -*-
"""
用户模块
"""
from flask import render_template, flash, redirect, url_for, current_app, request, Blueprint
from flask_login import login_required, current_user, fresh_login_required, logout_user

from albumy.decorators import confirm_required, permission_required
from albumy.emails import send_confirm_email
from albumy.extensions import db, avatars
from albumy.forms.user import EditProfileForm, UploadAvatarForm, CropAvatarForm, ChangeEmailForm, \
	ChangePasswordForm, NotificationSettingForm, PrivacySettingForm, DeleteAccountForm
from albumy.models import User, Photo, Collect
from albumy.notifications import push_follow_notification
from albumy.settings import Operations
from albumy.utils import generate_token, validate_token, redirect_back, flash_errors, logger

user_bp = Blueprint('user', __name__)


@user_bp.route('/<username>')
def index(username):
	"""
	用户主页
	:param username: 用户名
	"""
	logger.info('url = ' + str(request.url))
	user = User.query.filter_by(username=username).first_or_404()
	if user == current_user and user.locked:
		flash('抱歉，您的账号已被禁用该功能！', 'danger')

	# 用户被禁止登录
	if user == current_user and not user.active:
		logout_user()

	page = request.args.get('page', 1, type=int)
	per_page = current_app.config['ALBUMY_PHOTO_PER_PAGE']
	# 获取用户上传的图片
	pagination = Photo.query.with_parent(user).order_by(Photo.timestamp.desc()).paginate(page, per_page)
	photos = pagination.items
	return render_template('user/index.html', user=user, pagination=pagination, photos=photos)


@user_bp.route('/<username>/collections')
def show_collections(username):
	"""
	显示所有收藏的图片
	:param username: 用户名
	"""
	logger.info('url = ' + str(request.url))
	user = User.query.filter_by(username=username).first_or_404()
	page = request.args.get('page', 1, type=int)
	per_page = current_app.config['ALBUMY_PHOTO_PER_PAGE']
	# 所有收藏的数据
	pagination = Collect.query.with_parent(user).order_by(Collect.timestamp.desc()).paginate(page, per_page)
	collects = pagination.items
	return render_template('user/collections.html', user=user, pagination=pagination, collects=collects)


@user_bp.route('/follow/<username>', methods=['POST'])
@login_required
@confirm_required
@permission_required('FOLLOW')
def follow(username):
	"""
	关注其他用户
	:param username: 被关注者的用户名
	"""
	logger.info('url = ' + str(request.url))
	# 被关注者的实例对象
	user = User.query.filter_by(username=username).first_or_404()
	# 如果已经关注了，则返回
	if current_user.is_following(user):
		flash('已经关注该用户！', 'info')
		return redirect(url_for('.index', username=username))
	# 关注
	current_user.follow(user)
	flash('关注成功！', 'success')
	# 消息提醒
	if user.receive_follow_notification:
		push_follow_notification(follower=current_user, receiver=user)
	return redirect_back()


@user_bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
	"""
	取消关注
	:param username: 被关注者的用户名
	"""
	logger.info('url = ' + str(request.url))
	user = User.query.filter_by(username=username).first_or_404()
	# 在取消之前没有关注该用户
	if not current_user.is_following(user):
		flash('你没有关注该用户！', 'info')
		return redirect(url_for('.index', username=username))
	# 取消该用户
	current_user.unfollow(user)
	flash('取消关注成功！', 'info')
	return redirect_back()


@user_bp.route('/<username>/followers')
def show_followers(username):
	"""
	显示所有关注该用户的用户
	:param username: 用户名
	"""
	logger.info('url = ' + str(request.url))
	# 根据用户名获取User实例对象
	user = User.query.filter_by(username=username).first_or_404()
	page = request.args.get('page', 1, type=int)
	per_page = current_app.config['ALBUMY_USER_PER_PAGE']
	pagination = user.followers.paginate(page, per_page)
	# 得到所有的关注者User
	follows = pagination.items
	return render_template('user/followers.html', user=user, pagination=pagination, follows=follows)


@user_bp.route('/<username>/following')
def show_following(username):
	"""
	显示username用户所有关注的用户
	:param username: 用户名
	"""
	logger.info('url = ' + str(request.url))
	user = User.query.filter_by(username=username).first_or_404()
	page = request.args.get('page', 1, type=int)
	per_page = current_app.config['ALBUMY_USER_PER_PAGE']
	pagination = user.following.paginate(page, per_page)
	follows = pagination.items
	return render_template('user/following.html', user=user, pagination=pagination, follows=follows)


@user_bp.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
	"""
	编辑信息
	"""
	logger.info('url = ' + str(request.url))
	form = EditProfileForm()
	if form.validate_on_submit():
		current_user.name = form.name.data
		current_user.username = form.username.data
		current_user.bio = form.bio.data
		current_user.website = form.website.data
		current_user.location = form.location.data
		db.session.commit()
		flash('Profile updated.', 'success')
		return redirect(url_for('.index', username=current_user.username))
	form.name.data = current_user.name
	form.username.data = current_user.username
	form.bio.data = current_user.bio
	form.website.data = current_user.website
	form.location.data = current_user.location
	return render_template('user/settings/edit_profile.html', form=form)


@user_bp.route('/settings/avatar')
@login_required
@confirm_required
def change_avatar():
	"""
	修改头像
	"""
	logger.info('url = ' + str(request.url))
	upload_form = UploadAvatarForm()
	crop_form = CropAvatarForm()
	return render_template('user/settings/change_avatar.html', upload_form=upload_form, crop_form=crop_form)


@user_bp.route('/settings/avatar/upload', methods=['POST'])
@login_required
@confirm_required
def upload_avatar():
	"""
	更新头像
	"""
	logger.info('url = ' + str(request.url))
	form = UploadAvatarForm()
	if form.validate_on_submit():
		image = form.image.data
		filename = avatars.save_avatar(image)
		# 更新头像
		current_user.avatar_raw = filename
		db.session.commit()
		flash('文件已上传，请裁剪！', 'success')
	flash_errors(form)
	return redirect(url_for('.change_avatar'))


@user_bp.route('/settings/avatar/crop', methods=['POST'])
@login_required
@confirm_required
def crop_avatar():
	"""
	裁剪头像
	"""
	logger.info('url = ' + str(request.url))
	form = CropAvatarForm()
	if form.validate_on_submit():
		x = form.x.data
		y = form.y.data
		w = form.w.data
		h = form.h.data
		# 头像裁剪
		filenames = avatars.crop_avatar(current_user.avatar_raw, x, y, w, h)
		# 更新头像
		current_user.avatar_s = filenames[0]
		current_user.avatar_m = filenames[1]
		current_user.avatar_l = filenames[2]
		db.session.commit()
		flash('头像更新成功', 'success')
	flash_errors(form)
	return redirect(url_for('.change_avatar'))


@user_bp.route('/settings/change-password', methods=['GET', 'POST'])
@fresh_login_required
def change_password():
	"""
	修改密码
	"""
	logger.info('url = ' + str(request.url))
	form = ChangePasswordForm()
	if form.validate_on_submit() and current_user.validate_password(form.old_password.data):
		current_user.set_password(form.password.data)
		db.session.commit()
		flash('密码修改成功！', 'success')
		return redirect(url_for('.index', username=current_user.username))
	return render_template('user/settings/change_password.html', form=form)


@user_bp.route('/settings/change-email', methods=['GET', 'POST'])
@fresh_login_required
def change_email_request():
	"""
	发送修改邮箱的邮件
	"""
	logger.info('url = ' + str(request.url))
	form = ChangeEmailForm()
	if form.validate_on_submit():
		# 获取token
		token = generate_token(user=current_user, operation=Operations.CHANGE_EMAIL, new_email=form.email.data.lower())
		# 发送验证邮件
		send_confirm_email(to=form.email.data, user=current_user, token=token)
		flash('邮件已发送，请登录邮箱验证！', 'info')
		return redirect(url_for('.index', username=current_user.username))
	return render_template('user/settings/change_email.html', form=form)


@user_bp.route('/change-email/<token>')
@login_required
def change_email(token):
	"""
	修改邮箱
	:param token: 从邮箱中点击链接携带的token
	"""
	logger.info('url = ' + str(request.url))
	if validate_token(user=current_user, token=token, operation=Operations.CHANGE_EMAIL):
		flash('邮箱更新成功！', 'success')
		return redirect(url_for('.index', username=current_user.username))
	else:
		flash('无效或过期的token！', 'warning')
		return redirect(url_for('.change_email_request'))


@user_bp.route('/settings/notification', methods=['GET', 'POST'])
@login_required
def notification_setting():
	"""
	消息提醒设置
	"""
	logger.info('url = ' + str(request.url))
	form = NotificationSettingForm()
	if form.validate_on_submit():
		current_user.receive_collect_notification = form.receive_collect_notification.data
		current_user.receive_comment_notification = form.receive_comment_notification.data
		current_user.receive_follow_notification = form.receive_follow_notification.data
		db.session.commit()
		flash('消息提醒更新成功！', 'success')
		return redirect(url_for('.index', username=current_user.username))
	form.receive_collect_notification.data = current_user.receive_collect_notification
	form.receive_comment_notification.data = current_user.receive_comment_notification
	form.receive_follow_notification.data = current_user.receive_follow_notification
	return render_template('user/settings/edit_notification.html', form=form)


@user_bp.route('/settings/privacy', methods=['GET', 'POST'])
@login_required
def privacy_setting():
	"""
	隐私设置
	"""
	logger.info('url = ' + str(request.url))
	form = PrivacySettingForm()
	if form.validate_on_submit():
		current_user.public_collections = form.public_collections.data
		db.session.commit()
		flash('设置更新成功！', 'success')
		return redirect(url_for('.index', username=current_user.username))
	form.public_collections.data = current_user.public_collections
	return render_template('user/settings/edit_privacy.html', form=form)


@user_bp.route('/settings/account/delete', methods=['GET', 'POST'])
@fresh_login_required
def delete_account():
	"""
	删除账号
	"""
	logger.info('url = ' + str(request.url))
	form = DeleteAccountForm()
	if form.validate_on_submit():
		# 删除当前账号
		db.session.delete(current_user._get_current_object())
		db.session.commit()
		flash('账号已删除，如想再次加入，请重新注册！', 'success')
		return redirect(url_for('main.index'))
	return render_template('user/settings/delete_account.html', form=form)
