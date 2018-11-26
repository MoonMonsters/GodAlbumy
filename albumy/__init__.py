# -*- coding: utf-8 -*-
import os

import click
from flask import Flask, render_template
from flask_login import current_user
from flask_wtf.csrf import CSRFError

from albumy.blueprints.admin import admin_bp
from albumy.blueprints.ajax import ajax_bp
from albumy.blueprints.auth import auth_bp
from albumy.blueprints.main import main_bp
from albumy.blueprints.user import user_bp
from albumy.extensions import bootstrap, db, login_manager, mail, dropzone, moment, whooshee, avatars, csrf
from albumy.models import Role, User, Photo, Tag, Follow, Notification, Comment, Collect, Permission
from albumy.settings import config
from albumy.utils import logger


def create_app(config_name=None):
	logger.warning('start web')
	"""
	创建Flask对象并初始化程序
	"""
	if config_name is None:
		# 从环境中读取FLASK_CONFIG的值，即如果使用了flask-dotenv库的话，那么就会从.flaskenv文件中读取
		config_name = os.getenv('FLASK_CONFIG', 'development')

	app = Flask('albumy')
	# 加载配置
	app.config.from_object(config[config_name])

	# 注册各种功能
	register_extensions(app)
	register_blueprints(app)
	register_commands(app)
	register_errorhandlers(app)
	register_shell_context(app)
	register_template_context(app)

	return app


def register_extensions(app):
	"""
	注册第三方库对象
	"""
	bootstrap.init_app(app)
	db.init_app(app)
	login_manager.init_app(app)
	mail.init_app(app)
	dropzone.init_app(app)
	moment.init_app(app)
	whooshee.init_app(app)
	avatars.init_app(app)
	csrf.init_app(app)
	# cache.init_app(app)


def register_blueprints(app):
	"""
	注册蓝本
	"""
	# main是主界面
	app.register_blueprint(main_bp)
	app.register_blueprint(user_bp, url_prefix='/user')
	app.register_blueprint(auth_bp, url_prefix='/auth')
	app.register_blueprint(admin_bp, url_prefix='/admin')
	app.register_blueprint(ajax_bp, url_prefix='/ajax')


def register_shell_context(app):
	"""
	注册flask_shell
	"""

	@app.shell_context_processor
	def make_shell_context():
		"""
		当使用flask_shell时，直接可以使用db,User,Photo等类或者对象，不需要再导入
		:return:
		"""
		return dict(db=db, User=User, Photo=Photo, Tag=Tag,
					Follow=Follow, Collect=Collect, Comment=Comment,
					Notification=Notification)


def register_template_context(app):
	"""
	被app.context_processor装饰的值，可以在templates中全局使用
	"""

	@app.context_processor
	def make_template_context():
		if current_user.is_authenticated:
			# 如果用户已登录，则返回未读消息数量
			# with_parent起到关联User类的作用
			notification_count = Notification.query.with_parent(current_user).filter_by(is_read=False).count()
		else:
			notification_count = None
		# 可在templates中全局使用
		return dict(notification_count=notification_count)


def register_errorhandlers(app):
	"""
	错误处理
	"""

	@app.errorhandler(400)
	def bad_request(e):
		return render_template('errors/400.html'), 400

	@app.errorhandler(403)
	def forbidden(e):
		return render_template('errors/403.html'), 403

	@app.errorhandler(404)
	def page_not_found(e):
		return render_template('errors/404.html'), 404

	@app.errorhandler(413)
	def request_entity_too_large(e):
		return render_template('errors/413.html'), 413

	@app.errorhandler(500)
	def internal_server_error(e):
		"""
		服务器内部错误
		"""
		return render_template('errors/500.html'), 500

	@app.errorhandler(CSRFError)
	def handle_csrf_error(e):
		"""
		跨域错误
		"""
		return render_template('errors/400.html', description=e.description), 500


def register_commands(app):
	"""
	注册flask指令，即使用flask initdb操作完成对应功能
	"""

	@app.cli.command()
	@click.option('--drop', is_flag=True, help='Create after drop.')
	def initdb(drop):
		"""
		使用flask initdb清空数据库然后再初始化数据库
		"""
		if drop:
			click.confirm('该操作将会清空数据表数据，是否继续？', abort=True)
			db.drop_all()
			click.echo('Drop tables.')
		db.create_all()
		click.echo('Initialized database.')

	@app.cli.command()
	def init():
		"""
		初始化数据库
		"""
		click.echo('Initializing the database...')
		db.create_all()

		click.echo('Initializing the roles and permissions...')
		# 在Role类中，调用init_role函数将会初始化Role数据和Permission数据
		Role.init_role()

		click.echo('Done.')

	@app.cli.command()
	@click.option('--user', default=10, help='Quantity of users, default is 10.')
	@click.option('--follow', default=30, help='Quantity of follows, default is 50.')
	@click.option('--photo', default=30, help='Quantity of photos, default is 500.')
	@click.option('--tag', default=20, help='Quantity of tags, default is 500.')
	@click.option('--collect', default=50, help='Quantity of collects, default is 500.')
	@click.option('--comment', default=100, help='Quantity of comments, default is 500.')
	def fake(user, follow, photo, tag, collect, comment):
		"""
		使用flask fake创建虚拟数据
		"""

		from albumy.fakes import fake_admin, fake_comment, fake_follow, fake_photo, fake_tag, fake_user, fake_collect

		db.drop_all()
		db.create_all()

		click.echo('Initializing the roles and permissions...')
		Role.init_role()
		click.echo('Generating the administrator...')
		# 添加管理员账号
		fake_admin()
		click.echo('Generating %d users...' % user)
		# 随机用户数据
		fake_user(user)
		click.echo('Generating %d follows...' % follow)
		# 虚拟关注数据
		fake_follow(follow)
		click.echo('Generating %d tags...' % tag)
		# 虚拟标签
		fake_tag(tag)
		click.echo('Generating %d photos...' % photo)
		# 虚拟图片
		fake_photo(photo)
		click.echo('Generating %d collects...' % photo)
		# 随机收藏数据
		fake_collect(collect)
		click.echo('Generating %d comments...' % comment)
		# 虚拟评论
		fake_comment(comment)
		click.echo('Done.')
