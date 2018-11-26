# -*- coding: utf-8 -*-
import os
import random

from PIL import Image
from faker import Faker
from flask import current_app
from sqlalchemy.exc import IntegrityError

from albumy.extensions import db
from albumy.models import User, Photo, Tag, Comment, Notification

fake = Faker()


def fake_admin():
	"""
	创建管理员账号
	"""
	admin = User(
		name="FlynnGod",
		username="FlynnGod",
		email="qxinhai@yeah.net",
		bio=fake.sentence(),
		website="http://qxinhai.cn",
		confirmed=True,
	)
	admin.set_password("12345678")
	notification = Notification(message="Hello, welcome to Albumy.", receiver=admin)
	db.session.add(notification)
	db.session.add(admin)
	db.session.commit()


def fake_user(count=10):
	"""
	创建虚拟User数据
	"""
	for i in range(count):
		user = User(
			# 随机名字
			name=fake.name(),
			# 设置成True后，不需要通过邮件验证了
			confirmed=True,
			# 虚拟用户名
			username=fake.user_name(),
			bio=fake.sentence(),
			location=fake.city(),
			website=fake.url(),
			member_since=fake.date_this_decade(),
			email=fake.email(),
		)
		# 将所有密码都设置成固定的
		user.set_password("123456")
		db.session.add(user)
		try:
			# 防止提交失败
			db.session.commit()
		except IntegrityError:
			db.session.rollback()


def fake_follow(count=30):
	"""
	创建Follow对象
	"""
	for i in range(count):
		# 随机用户
		user = User.query.get(random.randint(1, User.query.count()))
		# user关注随机的User对象
		user.follow(User.query.get(random.randint(1, User.query.count())))
	db.session.commit()


def fake_tag(count=20):
	"""
	创建虚拟Tag对象
	"""
	for i in range(count):
		# 随机单词
		tag = Tag(name=fake.word())
		db.session.add(tag)
		try:
			db.session.commit()
		except IntegrityError:
			db.session.rollback()


def fake_photo(count=30):
	"""
	照片
	"""
	# 上传路径，从配置文件中读取
	upload_path = current_app.config["ALBUMY_UPLOAD_PATH"]
	for i in range(count):
		print(i)

		filename = "random_%d.jpg" % i
		# 随机颜色
		r = lambda: random.randint(128, 255)
		# 根据颜色得到图片对象
		img = Image.new(mode="RGB", size=(800, 800), color=(r(), r(), r()))
		# 保存图片
		img.save(os.path.join(upload_path, filename))

		# 创建Photo对象，并保存到数据库
		photo = Photo(
			# 随机文字
			description=fake.text(),
			filename=filename,
			filename_m=filename,
			filename_s=filename,
			# 随机User对象
			author=User.query.get(random.randint(1, User.query.count())),
			# 时间
			timestamp=fake.date_time_this_year(),
		)

		# 给图片添加随机1-5个Tag
		for j in range(random.randint(1, 5)):
			tag = Tag.query.get(random.randint(1, Tag.query.count()))
			if tag not in photo.tags:
				photo.tags.append(tag)

		db.session.add(photo)
	db.session.commit()


def fake_collect(count=50):
	"""
	用户收藏图片
	"""
	for i in range(count):
		# 随机用户
		user = User.query.get(random.randint(1, User.query.count()))
		# 随机图片
		user.collect(Photo.query.get(random.randint(1, Photo.query.count())))
	db.session.commit()


def fake_comment(count=100):
	"""
	评论
	"""
	for i in range(count):
		comment = Comment(
			# 随机用户
			author=User.query.get(random.randint(1, User.query.count())),
			# 评论内容
			body=fake.sentence(),
			# 时间
			timestamp=fake.date_time_this_year(),
			# 图片
			photo=Photo.query.get(random.randint(1, Photo.query.count())),
		)
		db.session.add(comment)
	db.session.commit()
