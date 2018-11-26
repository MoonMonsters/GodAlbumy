# -*- coding: utf-8 -*-
from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, HiddenField, ValidationError
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional, Regexp

from albumy.models import User


class EditProfileForm(FlaskForm):
	"""
	编辑个人信息
	"""
	name = StringField('名字', validators=[DataRequired(), Length(1, 30)])
	username = StringField('用户名', validators=[DataRequired(), Length(1, 20),
											  Regexp('^[a-zA-Z0-9]*$',
													 message='The username should contain only a-z, A-Z and 0-9.')])
	website = StringField('网站', validators=[Optional(), Length(0, 255)])
	location = StringField('城市', validators=[Optional(), Length(0, 50)])
	bio = TextAreaField('介绍', validators=[Optional(), Length(0, 120)])
	submit = SubmitField('修改')

	def validate_username(self, field):
		if field.data != current_user.username and User.query.filter_by(username=field.data).first():
			raise ValidationError('The username is already in use.')


class UploadAvatarForm(FlaskForm):
	"""
	上传头像
	"""
	image = FileField('上传', validators=[
		FileRequired(),
		FileAllowed(['jpg', 'png'], 'The file format should be .jpg or .png.')
	])
	submit = SubmitField('提交')


class CropAvatarForm(FlaskForm):
	"""
	裁剪上传的头像
	"""
	x = HiddenField()
	y = HiddenField()
	w = HiddenField()
	h = HiddenField()
	submit = SubmitField('修改')


class ChangeEmailForm(FlaskForm):
	"""
	修改邮箱
	"""
	email = StringField('新的邮箱', validators=[DataRequired(), Length(1, 254), Email()])
	submit = SubmitField('修改')


class ChangePasswordForm(FlaskForm):
	"""
	修改密码
	"""
	old_password = PasswordField('旧密码', validators=[DataRequired()])
	password = PasswordField('新密码', validators=[
		DataRequired(), Length(8, 128), EqualTo('password2')])
	password2 = PasswordField('重复密码', validators=[DataRequired()])
	submit = SubmitField('修改')


class NotificationSettingForm(FlaskForm):
	"""
	消息提醒设置
	"""
	receive_comment_notification = BooleanField('新评论')
	receive_follow_notification = BooleanField('新关注者')
	receive_collect_notification = BooleanField('新收藏者')
	submit = SubmitField('修改')


class PrivacySettingForm(FlaskForm):
	"""
	私人设置
	"""
	public_collections = BooleanField('是否公开我的收藏')
	submit = SubmitField('修改')


class DeleteAccountForm(FlaskForm):
	"""
	删除个人账号
	"""
	username = StringField('用户名', validators=[DataRequired(), Length(1, 20)])
	submit = SubmitField('删除')

	def validate_username(self, field):
		if field.data != current_user.username:
			raise ValidationError('错误的用户名')
