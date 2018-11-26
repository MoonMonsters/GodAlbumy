# -*- coding: utf-8 -*-
from wtforms import StringField, SelectField, BooleanField, SubmitField
from wtforms import ValidationError
from wtforms.validators import DataRequired, Length, Email

from albumy.forms.user import EditProfileForm
from albumy.models import User, Role


class EditProfileAdminForm(EditProfileForm):
	"""
	修改用户信息
	"""
	# 邮箱
	email = StringField('邮箱', validators=[DataRequired(), Length(1, 254), Email()])
	# 角色
	role = SelectField('角色', coerce=int)
	# 是否禁止登录
	active = BooleanField('是否禁止登录')
	# 是否验证
	confirmed = BooleanField('邮箱是否通过验证')
	submit = SubmitField('修改')

	def __init__(self, user, *args, **kwargs):
		super(EditProfileAdminForm, self).__init__(*args, **kwargs)
		self.role.choices = [(role.id, role.name)
							 for role in Role.query.order_by(Role.name).all()]
		self.user = user

	def validate_username(self, field):
		if field.data != self.user.username and User.query.filter_by(email=field.data).first():
			raise ValidationError('The username is already in use.')

	def validate_email(self, field):
		if field.data != self.user.email and User.query.filter_by(email=field.data).first():
			raise ValidationError('The email is already in use.')
