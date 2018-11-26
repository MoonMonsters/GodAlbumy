# -*- coding: utf-8 -*-
import os
from datetime import datetime

from flask import current_app
from flask_avatars import Identicon
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from albumy.extensions import db, whooshee

# 关联表，关联Role和Permission
roles_permissions = db.Table(
	"roles_permissions",
	db.Column("role_id", db.Integer, db.ForeignKey("role.id")),
	db.Column("permission_id", db.Integer, db.ForeignKey("permission.id")),
)


class Permission(db.Model):
	"""
	权限表，给用户设置权限
	"""
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(30), unique=True)
	roles = db.relationship(
		"Role", secondary=roles_permissions, back_populates="permissions"
	)


class Role(db.Model):
	"""
	角色表，即可拥有的权限
	"""
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(30), unique=True)
	# 关联到用户
	users = db.relationship("User", back_populates="role")
	# 权限
	permissions = db.relationship(
		"Permission", secondary=roles_permissions, back_populates="roles"
	)

	@staticmethod
	def init_role():
		"""
		初始化角色和权限信息
		"""
		roles_permissions_map = {
			# 被禁用户
			"Locked": ["FOLLOW", "COLLECT"],
			# 普通用户
			"User": ["FOLLOW", "COLLECT", "COMMENT", "UPLOAD"],
			# 管理资源权限
			"Moderator": ["FOLLOW", "COLLECT", "COMMENT", "UPLOAD", "MODERATE"],
			# 管理员
			"Administrator": [
				"FOLLOW",  # 关注用户
				"COLLECT",  # 收藏图片
				"COMMENT",  # 评论
				"UPLOAD",  # 上传
				"MODERATE",  # 修改
				"ADMINISTER",  # 管理
			],
		}

		# 遍历
		for role_name in roles_permissions_map:
			# 取出Role对象，如果没有则创建
			role = Role.query.filter_by(name=role_name).first()
			if role is None:
				role = Role(name=role_name)
				db.session.add(role)
			role.permissions = []
			# 遍历每一种角色拥有的权限
			for permission_name in roles_permissions_map[role_name]:
				# 如果该角色在数据表中不存在，则创建
				permission = Permission.query.filter_by(name=permission_name).first()
				if permission is None:
					permission = Permission(name=permission_name)
					db.session.add(permission)
				# 追加到Role对象下
				role.permissions.append(permission)
		db.session.commit()


class Follow(db.Model):
	"""
	关注用户
	"""
	# 关注者
	follower_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
	# 被关注者
	followed_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
	# 时间
	timestamp = db.Column(db.DateTime, default=datetime.utcnow)

	# 关注者和被关注者都是自身
	follower = db.relationship(
		"User", foreign_keys=[follower_id], back_populates="following", lazy="joined"
	)
	followed = db.relationship(
		"User", foreign_keys=[followed_id], back_populates="followers", lazy="joined"
	)


class Collect(db.Model):
	"""
	收藏图片
	"""
	# 用户id
	collector_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
	# 图片id
	collected_id = db.Column(db.Integer, db.ForeignKey("photo.id"), primary_key=True)
	# 时间
	timestamp = db.Column(db.DateTime, default=datetime.utcnow)

	collector = db.relationship("User", back_populates="collections", lazy="joined")
	collected = db.relationship("Photo", back_populates="collectors", lazy="joined")


@whooshee.register_model("name", "username")
class User(db.Model, UserMixin):
	id = db.Column(db.Integer, primary_key=True)
	# 用户名，唯一，索引
	username = db.Column(db.String(20), unique=True, index=True)
	# 邮箱，唯一，索引
	email = db.Column(db.String(254), unique=True, index=True)
	password_hash = db.Column(db.String(128))
	name = db.Column(db.String(30))
	website = db.Column(db.String(255))
	bio = db.Column(db.String(120))
	location = db.Column(db.String(50))
	# 注册时间
	member_since = db.Column(db.DateTime, default=datetime.utcnow)
	# 小头像
	avatar_s = db.Column(db.String(64))
	# 中头像
	avatar_m = db.Column(db.String(64))
	# 大头像
	avatar_l = db.Column(db.String(64))
	# 自定义头像
	avatar_raw = db.Column(db.String(64))
	# 是否验证
	confirmed = db.Column(db.Boolean, default=False)
	# 是否被禁，可以登录但无法使用某些功能
	locked = db.Column(db.Boolean, default=False)
	# 是否允许登录，禁止登录
	active = db.Column(db.Boolean, default=True)
	# 关注
	public_collections = db.Column(db.Boolean, default=True)
	# 是否接收评论提醒
	receive_comment_notification = db.Column(db.Boolean, default=True)
	# 是否接收关注提醒
	receive_follow_notification = db.Column(db.Boolean, default=True)
	# 是否接收收藏提醒
	receive_collect_notification = db.Column(db.Boolean, default=True)

	role_id = db.Column(db.Integer, db.ForeignKey("role.id"))

	role = db.relationship("Role", back_populates="users")
	photos = db.relationship("Photo", back_populates="author", cascade="all")
	comments = db.relationship("Comment", back_populates="author", cascade="all")
	notifications = db.relationship(
		"Notification", back_populates="receiver", cascade="all"
	)
	collections = db.relationship("Collect", back_populates="collector", cascade="all")
	following = db.relationship(
		"Follow",
		foreign_keys=[Follow.follower_id],
		back_populates="follower",
		lazy="dynamic",
		cascade="all",
	)
	followers = db.relationship(
		"Follow",
		foreign_keys=[Follow.followed_id],
		back_populates="followed",
		lazy="dynamic",
		cascade="all",
	)

	def __init__(self, **kwargs):
		super(User, self).__init__(**kwargs)
		self.generate_avatar()
		self.follow(self)
		# 设置角色
		self.set_role()

	def set_password(self, password):
		"""
		设置密码
		"""
		# generate_password_hash是flask自带的，对密码进行加密的函数
		self.password_hash = generate_password_hash(password)

	def set_role(self):
		if self.role is None:
			# 判断是不是管理员，如果是管理员，则设置管理员身份，否则就是普通用户
			# 根据设置中的邮箱匹配
			if self.email == current_app.config["ALBUMY_ADMIN_EMAIL"]:
				self.role = Role.query.filter_by(name="Administrator").first()
			else:
				self.role = Role.query.filter_by(name="User").first()
			db.session.commit()

	def validate_password(self, password):
		"""
		验证密码是否匹配
		数据库中对密码加密了，并且只能加密，无法解密
		通过flask自带的check_password_hash判断输入的密码和存储的密码是否匹配
		"""
		return check_password_hash(self.password_hash, password)

	def follow(self, user):
		"""
		关注用户
		"""
		if not self.is_following(user):
			# 如果没有关注，则关注
			follow = Follow(follower=self, followed=user)
			db.session.add(follow)
			db.session.commit()

	def unfollow(self, user):
		"""
		取消关注
		"""
		follow = self.following.filter_by(followed_id=user.id).first()
		if follow:
			db.session.delete(follow)
			db.session.commit()

	def is_following(self, user):
		"""
		判断是否关注
		"""
		if user.id is None:
			return False
		return self.following.filter_by(followed_id=user.id).first() is not None

	def is_followed_by(self, user):
		# TODO
		return self.followers.filter_by(follower_id=user.id).first() is not None

	@property
	def followed_photos(self):
		# TODO
		return Photo.query.join(Follow, Follow.followed_id == Photo.author_id).filter(
			Follow.follower_id == self.id
		)

	def collect(self, photo):
		"""
		收藏图片
		"""
		if not self.is_collecting(photo):
			collect = Collect(collector=self, collected=photo)
			db.session.add(collect)
			db.session.commit()

	def uncollect(self, photo):
		"""
		取消收藏
		"""
		collect = (
			Collect.query.with_parent(self).filter_by(collected_id=photo.id).first()
		)
		if collect:
			db.session.delete(collect)
			db.session.commit()

	def is_collecting(self, photo):
		"""
		判断是否收藏
		"""
		return (
				Collect.query.with_parent(self).filter_by(collected_id=photo.id).first()
				is not None
		)

	def lock(self):
		"""
		禁用用户
		"""
		self.locked = True
		self.role = Role.query.filter_by(name="Locked").first()
		db.session.commit()

	def unlock(self):
		"""
		取消禁用
		"""
		self.locked = False
		self.role = Role.query.filter_by(name="User").first()
		db.session.commit()

	def block(self):
		self.active = False
		db.session.commit()

	def unblock(self):
		self.active = True
		db.session.commit()

	def generate_avatar(self):
		avatar = Identicon()
		filenames = avatar.generate(text=self.username)
		self.avatar_s = filenames[0]
		self.avatar_m = filenames[1]
		self.avatar_l = filenames[2]
		db.session.commit()

	@property
	def is_admin(self):
		"""
		是否为管理员
		"""
		return self.role.name == "Administrator"

	@property
	def is_active(self):
		"""
		是否为激活状态
		LoginManager中需要实现该函数
		:return: 如果是，返回True
		"""
		return self.active

	def can(self, permission_name):
		"""
		判断权限问题，是否有权限做某事
		"""
		permission = Permission.query.filter_by(name=permission_name).first()
		return (
				permission is not None
				and self.role is not None
				and permission in self.role.permissions
		)


tagging = db.Table(
	"tagging",
	db.Column("photo_id", db.Integer, db.ForeignKey("photo.id")),
	db.Column("tag_id", db.Integer, db.ForeignKey("tag.id")),
)


@whooshee.register_model("description")
class Photo(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	# 描述
	description = db.Column(db.String(500))
	# 文件名
	filename = db.Column(db.String(64))
	# 小图
	filename_s = db.Column(db.String(64))
	# 中图
	filename_m = db.Column(db.String(64))
	# 时间
	timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
	# 是否可评论
	can_comment = db.Column(db.Boolean, default=True)
	# 被举报次数
	flag = db.Column(db.Integer, default=0)
	# 用户
	author_id = db.Column(db.Integer, db.ForeignKey("user.id"))

	author = db.relationship("User", back_populates="photos")
	# 评论
	comments = db.relationship("Comment", back_populates="photo", cascade="all")
	# 收藏
	collectors = db.relationship("Collect", back_populates="collected", cascade="all")
	tags = db.relationship("Tag", secondary=tagging, back_populates="photos")


@whooshee.register_model("name")
class Tag(db.Model):
	"""
	图片标签
	"""
	id = db.Column(db.Integer, primary_key=True)
	# 标签名称
	name = db.Column(db.String(64), index=True, unique=True)

	photos = db.relationship("Photo", secondary=tagging, back_populates="tags")


class Comment(db.Model):
	"""
	评论
	"""
	id = db.Column(db.Integer, primary_key=True)
	# 内容
	body = db.Column(db.Text)
	# 时间
	timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
	# 举报次数
	flag = db.Column(db.Integer, default=0)

	# 回复
	replied_id = db.Column(db.Integer, db.ForeignKey("comment.id"))
	author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
	photo_id = db.Column(db.Integer, db.ForeignKey("photo.id"))

	photo = db.relationship("Photo", back_populates="comments")
	author = db.relationship("User", back_populates="comments")
	replies = db.relationship("Comment", back_populates="replied", cascade="all")
	replied = db.relationship("Comment", back_populates="replies", remote_side=[id])


class Notification(db.Model):
	"""
	消息提醒
	"""
	id = db.Column(db.Integer, primary_key=True)
	# 消息内容
	message = db.Column(db.Text, nullable=False)
	# 是否已阅读
	is_read = db.Column(db.Boolean, default=False)
	# 时间
	timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
	# 接收者的id
	receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"))

	receiver = db.relationship("User", back_populates="notifications")


# 监听器，监听删除用户对象这个动作
# 删除用户后，用户数据全部消息，同时从文件夹中删除用户头像
@db.event.listens_for(User, "after_delete", named=True)
def delete_avatars(**kwargs):
	"""
	删除头像
	"""
	target = kwargs["target"]
	for filename in [
		target.avatar_s,
		target.avatar_m,
		target.avatar_l,
		target.avatar_raw,
	]:
		# 需要加上判断，因为avatar_raw(自定义头像)有可能为空
		if filename is not None:
			# 头像路径
			path = os.path.join(current_app.config["AVATARS_SAVE_PATH"], filename)
			# 判断是否存在
			if os.path.exists(path):
				# 删除
				os.remove(path)


# 监听器，监听删除Photo对象这个操作
@db.event.listens_for(Photo, "after_delete", named=True)
def delete_photos(**kwargs):
	target = kwargs["target"]
	# 删除文件夹中所有的图片
	for filename in [target.filename, target.filename_s, target.filename_m]:
		path = os.path.join(current_app.config["ALBUMY_UPLOAD_PATH"], filename)
		if os.path.exists(path):  # not every filename map a unique file
			os.remove(path)
