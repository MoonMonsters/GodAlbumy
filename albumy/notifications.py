# -*- coding: utf-8 -*-
from flask import url_for

from albumy.extensions import db
from albumy.models import Notification


def push_follow_notification(follower, receiver):
	"""
	有新用户关注
	:param follower: 关注者
	:param receiver: 接收消息用户对象
	"""
	# 两个参数分别是用户首页，和关注者的用户名
	message = '用户 <a href="%s">%s</a> 关注了你。' % (
		url_for("user.index", username=follower.username),
		follower.username,
	)
	# 将message发送给receiver
	notification = Notification(message=message, receiver=receiver)
	# 存入数据库
	db.session.add(notification)
	db.session.commit()


def push_comment_notification(photo_id, receiver, page=1):
	"""
	有新评论消息提醒
	:param photo_id: 图片id
	:param receiver: 接收者
	:param page: 页码
	"""
	message = '<a href="%s#comments">图片</a> 有新的评论\回复' % (
		url_for("main.show_photo", photo_id=photo_id, page=page)
	)
	notification = Notification(message=message, receiver=receiver)
	db.session.add(notification)
	db.session.commit()


def push_collect_notification(collector, photo_id, receiver):
	"""
	有新的收藏消息提醒
	:param collector: 收藏者对象
	:param photo_id: 图片id
	:param receiver: 接收消息对象
	"""
	message = '用户 <a href="%s">%s</a> 收藏了你的 <a href="%s">图片</a>' % (
		# 用户主页和用户名
		url_for("user.index", username=collector.username),
		collector.username,
		# 图片
		url_for("main.show_photo", photo_id=photo_id),
	)
	notification = Notification(message=message, receiver=receiver)
	db.session.add(notification)
	db.session.commit()
