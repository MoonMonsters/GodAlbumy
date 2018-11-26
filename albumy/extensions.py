# -*- coding: utf-8 -*-
"""
第三方库 类对象
"""
from flask_avatars import Avatars
from flask_bootstrap import Bootstrap
from flask_dropzone import Dropzone
from flask_login import LoginManager, AnonymousUserMixin
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_whooshee import Whooshee
from flask_wtf import CSRFProtect
# from flask_cache import Cache

# from flask.ext.cache import Cache

bootstrap = Bootstrap()
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
dropzone = Dropzone()
moment = Moment()
whooshee = Whooshee()
avatars = Avatars()
csrf = CSRFProtect()
# cache = Cache()


# 这个回调被用来从对话里存储的用户ID中重新加载用户对象
# 它应该获取用户的unicode ID，以及返回对应的用户对象。
@login_manager.user_loader
def load_user(user_id):
	from albumy.models import User
	user = User.query.get(int(user_id))
	return user


# 当未登录用户访问一个需要登录才能访问的视图时，则重定向到该视图去
login_manager.login_view = 'auth.login'
# 默认flash工具发出的信息是Please log in to access this page。
# 可以通过设置LoginManager.login_message来自定义这段信息
# login_manager.login_message = 'Your custom message'
# 通过LoginManager.login_message_category，自定义消息类型
login_manager.login_message_category = 'warning'

# 需要重新验证身份
# 在某些情况下，用户设置的保存密码自动登录，那么当用户需要修改密码时，那么需要重新输入密码
# 跳转到设置好的页面中
login_manager.refresh_view = 'auth.re_authenticate'
# 消息类型
# login_manager.needs_refresh_message = 'Your custom message'
login_manager.needs_refresh_message_category = 'warning'


# 匿名用户，即未登录用户
class Guest(AnonymousUserMixin):
	# User类中有该函数，并且会使用current_user调用，所以匿名类也需要实现该函数
	def can(self, permission_name):
		return False

	# 判断是否是管理员
	@property
	def is_admin(self):
		return False


# 设置匿名用户，即未登录用户
login_manager.anonymous_user = Guest
