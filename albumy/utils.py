# -*- coding: utf-8 -*-
import os
import uuid
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

try:
	from urlparse import urlparse, urljoin
except ImportError:
	from urllib.parse import urlparse, urljoin

import PIL
from PIL import Image
from flask import current_app, request, url_for, redirect, flash
from itsdangerous import BadSignature, SignatureExpired
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from albumy.extensions import db
from albumy.models import User
from albumy.settings import Operations


def generate_token(user, operation, expire_in=None, **kwargs):
	"""
	获取token
	:param user: User实例对象
	:param operation: 邮箱操作类型
	:param expire_in: 过期时间
	:param kwargs: 更多其他数据
	:return: 加密后的token数据
	"""
	# TimedJSONWebSignatureSerializer的对象dumps之后的token数据中，会自动添加一个
	# timestamp，用来判断该token是否过期，就不用存入redis或者数据库了
	s = Serializer(current_app.config['SECRET_KEY'], expire_in)

	data = {'id': user.id, 'operation': operation}
	data.update(**kwargs)
	return s.dumps(data)


def validate_token(user, token, operation, new_password=None):
	"""
	验证token是否有效或者过期
	:param user: User实例对象
	:param token: token值
	:param operation: 操作
	:param new_password: 新的密码，在重置时可以用上
	:return: 验证结果
	"""
	s = Serializer(current_app.config['SECRET_KEY'])

	try:
		# 解析
		data = s.loads(token)
	except (SignatureExpired, BadSignature):
		return False

	# 判断operation和user.id是否匹配
	if operation != data.get('operation') or user.id != data.get('id'):
		return False

	# 具体操作
	# 邮箱验证通过
	if operation == Operations.CONFIRM:
		user.confirmed = True
	# 重设密码，然后更新数据库中的密码
	elif operation == Operations.RESET_PASSWORD:
		user.set_password(new_password)
	# 修改邮箱，更新数据库中的用户的邮箱
	elif operation == Operations.CHANGE_EMAIL:
		new_email = data.get('new_email')
		if new_email is None:
			return False
		if User.query.filter_by(email=new_email).first() is not None:
			return False
		user.email = new_email
	else:
		return False

	db.session.commit()
	return True


def rename_image(old_filename):
	"""
	重命名图片名字
	:param old_filename: 旧的文件名
	:return: 新的文件名
	"""
	# 得到后缀
	ext = os.path.splitext(old_filename)[1]
	# 随机产生一个uuid的16进制数据
	new_filename = uuid.uuid4().hex + ext
	return new_filename


def resize_image(image, filename, base_width):
	"""
	使用PIL库重新设置图片的尺寸大小
	:param image: 图片
	:param filename: 文件名
	:param base_width: 需要调整的基准值
	:return: 返回新的文件名
	"""
	filename, ext = os.path.splitext(filename)
	img = Image.open(image)
	# 如何要求，不用调整
	if img.size[0] <= base_width:
		return filename + ext
	# 宽的百分比
	w_percent = (base_width / float(img.size[0]))
	# 调整高度
	h_size = int((float(img.size[1]) * float(w_percent)))
	# 重设图片大小
	img = img.resize((base_width, h_size), PIL.Image.ANTIALIAS)

	# 给图片添加后缀
	# 在settings.py中，有两个属性，ALBUMY_PHOTO_SIZE 和 ALBUMY_PHOTO_SUFFIX
	# 根据base_width值的大小，可以得到后缀，即_s 或者 _m
	filename += current_app.config['ALBUMY_PHOTO_SUFFIX'][base_width] + ext
	# 保存到对应路径，并压缩
	img.save(os.path.join(current_app.config['ALBUMY_UPLOAD_PATH'], filename), optimize=True, quality=85)
	return filename


def is_safe_url(target):
	"""
	判断是否是安全链接
	"""
	ref_url = urlparse(request.host_url)
	test_url = urlparse(urljoin(request.host_url, target))
	return test_url.scheme in ('http', 'https') and \
		   ref_url.netloc == test_url.netloc


def redirect_back(default='main.index', **kwargs):
	"""
	返回到跳转之前的页面
	:param default: 默认是主页
	"""
	# 判断是否有next的值或者referrer的值
	# next表示下一步跳转的页面
	# referrer表示在哪一个页面跳转的
	for target in request.args.get('next'), request.referrer:
		if not target:
			continue
		if is_safe_url(target):
			return redirect(target)
	return redirect(url_for(default, **kwargs))


def flash_errors(form):
	"""
	flash消息
	"""
	for field, errors in form.errors.items():
		for error in errors:
			flash(u"Error in the %s field - %s" % (
				getattr(form, field).label.text,
				error
			))


def _log():
	# 创建logger，如果参数为空则返回root logger
	logger = logging.getLogger("Albumy")
	logger.setLevel(logging.INFO)  # 设置logger日志等级
	# 这里进行判断，如果logger.handlers列表为空，则添加，否则，直接去写日志
	if not logger.handlers:
		# 创建handler
		fh = RotatingFileHandler("logs/test.log", maxBytes=100 * 1024 * 1024, encoding="utf-8", mode="a",
								 backupCount=10)
		ch = logging.StreamHandler()
		# 设置输出日志格式
		formatter = logging.Formatter(
			fmt="%(asctime)s %(thread)d %(filename)s %(funcName)s %(lineno)d %(message)s",
			datefmt="%Y/%m/%d %X",
		)
		# 为handler指定输出格式
		fh.setFormatter(formatter)
		ch.setFormatter(formatter)
		# 为logger添加的日志处理器
		logger.addHandler(fh)
		logger.addHandler(ch)

	logger.debug(msg="\n" * 10)
	logger.debug(msg="now time is " + str(datetime.now()))
	logger.debug("-" * 80)

	return logger  # 直接返回logger


logger = _log()
