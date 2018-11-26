# -*- coding: utf-8 -*-
"""
ajax功能模块
"""
from flask import render_template, jsonify, Blueprint,request
from flask_login import current_user

from albumy.models import User, Photo, Notification
from albumy.notifications import push_collect_notification, push_follow_notification
from albumy.utils import logger

ajax_bp = Blueprint('ajax', __name__)


@ajax_bp.route('/notifications-count')
def notifications_count():
	"""
	未读消息数量
	:return: json格式的数据，包含了未读的数量
	"""
	logger.info('url = ' + str(request.url))
	if not current_user.is_authenticated:
		return jsonify(message='Login required.'), 403
	# 使用with_parent与user关联
	count = Notification.query.with_parent(current_user).filter_by(is_read=False).count()
	return jsonify(count=count)


@ajax_bp.route('/profile/<int:user_id>')
def get_profile(user_id):
	"""
	将鼠标移动到用户小头像上，弹出的用户信息
	:param user_id: 用户id
	"""
	logger.info('url = ' + str(request.url))
	user = User.query.get_or_404(user_id)
	return render_template('main/profile_popup.html', user=user)


@ajax_bp.route('/followers-count/<int:user_id>')
def followers_count(user_id):
	"""
	获取被关注者的数量
	:param user_id: 用户id
	"""
	logger.info('url = ' + str(request.url))
	user = User.query.get_or_404(user_id)
	count = user.followers.count() - 1
	return jsonify(count=count)


@ajax_bp.route('/<int:photo_id>/followers-count')
def collectors_count(photo_id):
	"""
	收藏该图片的用户数量
	:param photo_id: 图片id
	"""
	logger.info('url = ' + str(request.url))
	photo = Photo.query.get_or_404(photo_id)
	count = len(photo.collectors)
	return jsonify(count=count)


@ajax_bp.route('/collect/<int:photo_id>', methods=['POST'])
def collect(photo_id):
	"""
	收藏图片
	:param photo_id: 图片id
	"""
	logger.info('url = ' + str(request.url))
	# 用户没有登录
	if not current_user.is_authenticated:
		return jsonify(message='Login required.'), 403
	# 用户没有验证邮箱
	if not current_user.confirmed:
		return jsonify(message='Confirm account required.'), 400
	# 用户没有COLLECT权限
	if not current_user.can('COLLECT'):
		return jsonify(message='No permission.'), 403

	# 获取Photo实例对象，判断用户是否已经收藏过了
	photo = Photo.query.get_or_404(photo_id)
	if current_user.is_collecting(photo):
		return jsonify(message='Already collected.'), 400

	# 收藏图片
	current_user.collect(photo)
	# 如果登录用户不是图片作者，并且图片作者开启了接收消息通知功能，就将收藏图片消息发送给图片作者
	if current_user != photo.author and photo.author.receive_collect_notification:
		push_collect_notification(collector=current_user, photo_id=photo_id, receiver=photo.author)
	return jsonify(message='Photo collected.')


@ajax_bp.route('/uncollect/<int:photo_id>', methods=['POST'])
def uncollect(photo_id):
	"""
	取消收藏
	:param photo_id: 图片id
	"""
	logger.info('url = ' + str(request.url))
	# 如果用户没有登录，抛出403错误
	if not current_user.is_authenticated:
		return jsonify(message='Login required.'), 403

	# 如果用户没有收藏该图片却取消收藏，则抛出400错误
	photo = Photo.query.get_or_404(photo_id)
	if not current_user.is_collecting(photo):
		return jsonify(message='Not collect yet.'), 400

	# 取消收藏图片
	current_user.uncollect(photo)
	return jsonify(message='Collect canceled.')


@ajax_bp.route('/follow/<username>', methods=['POST'])
def follow(username):
	"""
	关注用户
	:param username: 用户名
	"""
	logger.info('url = ' + str(request.url))
	# 用户没有登录
	if not current_user.is_authenticated:
		return jsonify(message='Login required.'), 403
	# 用户没有验证邮箱
	if not current_user.confirmed:
		return jsonify(message='Confirm account required.'), 400
	# 没有没有FOLLOW权限
	if not current_user.can('FOLLOW'):
		return jsonify(message='No permission.'), 403

	# 获取被关注的User实例对象
	user = User.query.filter_by(username=username).first_or_404()
	if current_user.is_following(user):
		return jsonify(message='Already followed.'), 400

	# 关注
	current_user.follow(user)
	# 发送提醒消息
	if user.receive_collect_notification:
		push_follow_notification(follower=current_user, receiver=user)
	return jsonify(message='User followed.')


@ajax_bp.route('/unfollow/<username>', methods=['POST'])
def unfollow(username):
	"""
	取消收藏
	:param username: 用户名
	"""
	logger.info('url = ' + str(request.url))
	if not current_user.is_authenticated:
		return jsonify(message='Login required.'), 403

	user = User.query.filter_by(username=username).first_or_404()
	if not current_user.is_following(user):
		return jsonify(message='Not follow yet.'), 400

	current_user.unfollow(user)
	return jsonify(message='Follow canceled.')
