# -*- coding: utf-8 -*-
import os
import sys
import uuid

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# 将数据存入Sqlite中，需要判断是windows系统还是linux系统
WIN = sys.platform.startswith('win')
if WIN:
	prefix = 'sqlite:///'
else:
	prefix = 'sqlite:////'


class Operations:
	"""
	邮箱操作类型
	"""
	# 验证邮箱
	CONFIRM = 'confirm'
	# 重置密码
	RESET_PASSWORD = 'reset-password'
	# 修改邮箱
	CHANGE_EMAIL = 'change-email'


class BaseConfig:
	"""
	共有配置
	"""
	# 设置管理员邮箱\账号
	ALBUMY_ADMIN_EMAIL = os.getenv('ALBUMY_ADMIN', 'qxinhai@yeah.net')
	# 每一页显示图片数量
	ALBUMY_PHOTO_PER_PAGE = 12
	# 每一页显示评论数量
	ALBUMY_COMMENT_PER_PAGE = 15
	# 每一页显示消息提醒数量
	ALBUMY_NOTIFICATION_PER_PAGE = 20
	# 每一页显示用户数量
	ALBUMY_USER_PER_PAGE = 20
	# 管理图片
	ALBUMY_MANAGE_PHOTO_PER_PAGE = 20
	# 管理用户
	ALBUMY_MANAGE_USER_PER_PAGE = 30
	# 管理标签
	ALBUMY_MANAGE_TAG_PER_PAGE = 50
	# 管理评论
	ALBUMY_MANAGE_COMMENT_PER_PAGE = 30
	# 显示搜索结果数量
	ALBUMY_SEARCH_RESULT_PER_PAGE = 20
	# 邮件前缀
	ALBUMY_MAIL_SUBJECT_PREFIX = '[Albumy]'
	# 图片上传路径
	ALBUMY_UPLOAD_PATH = os.path.join(basedir, 'uploads')
	# 图片大小，小图400，中图800，大图就是默认上传的大小
	ALBUMY_PHOTO_SIZE = {'small': 400,
						 'medium': 800}
	# 上传图片名后缀
	ALBUMY_PHOTO_SUFFIX = {
		ALBUMY_PHOTO_SIZE['small']: '_s',  # 缩略图
		ALBUMY_PHOTO_SIZE['medium']: '_m',
	}

	SECRET_KEY = str(uuid.uuid4().hex)
	MAX_CONTENT_LENGTH = 3 * 1024 * 1024

	BOOTSTRAP_SERVE_LOCAL = True

	SQLALCHEMY_TRACK_MODIFICATIONS = False

	# 头像上传路径
	AVATARS_SAVE_PATH = os.path.join(ALBUMY_UPLOAD_PATH, 'avatars')
	# 头像大小，对应小头像，中头像，大头像
	AVATARS_SIZE_TUPLE = (30, 100, 200)

	# 邮箱配置
	# 其中，MAIL_SERVER，MAIL_USERNAME，MAIL_PASSWORD是从.flaskenv文件中读取
	# 该文件不会上传到公共空间中
	MAIL_SERVER = os.getenv('MAIL_SERVER')
	MAIL_PORT = 465
	MAIL_SUPPRESS_SEND = False
	MAIL_USE_SSL = True
	MAIL_USE_TLS = False
	MAIL_USERNAME = os.getenv('MAIL_USERNAME')
	MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
	MAIL_DEFAULT_SENDER = ('Albumy Admin', MAIL_USERNAME)

	# 使用flask-dropzone插件时，允许上传的文件类型
	DROPZONE_ALLOWED_FILE_TYPE = 'image'
	# 设置单个文件最大的大小为3M，否则报403错误
	DROPZONE_MAX_FILE_SIZE = 3
	# 单次最大上传为30张图片
	DROPZONE_MAX_FILES = 30
	# 是否需要CSRF验证
	DROPZONE_ENABLE_CSRF = True
	# TODO
	WHOOSHEE_MIN_STRING_LEN = 1

	# redis缓存
	CACHE_REDIS_URL = "redis://localhost:6379/2"
	CACHE_TYPE = 'redis'


class DevelopmentConfig(BaseConfig):
	"""
	开发环境
	"""
	# 设置数据库
	SQLALCHEMY_DATABASE_URI = \
		prefix + os.path.join(basedir, 'data-dev.db')


class TestingConfig(BaseConfig):
	"""
	测试环境
	"""
	TESTING = True
	WTF_CSRF_ENABLED = False
	SQLALCHEMY_DATABASE_URI = 'sqlite:///'  # in-memory database


class ProductionConfig(BaseConfig):
	"""
	正式上线环境
	"""
	SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL',
										prefix + os.path.join(basedir, 'data.db'))
	DEBUG = False


config = {
	'development': DevelopmentConfig,
	'testing': TestingConfig,
	'production': ProductionConfig,
}
