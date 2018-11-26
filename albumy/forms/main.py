# -*- coding: utf-8 -*-
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional, Length


class DescriptionForm(FlaskForm):
	"""
	描述
	"""
	description = TextAreaField('编辑描述', validators=[Optional(), Length(0, 500)])
	submit = SubmitField('提交')


class TagForm(FlaskForm):
	"""
	标签
	"""
	tag = StringField('添加标签', validators=[Optional(), Length(0, 64)])
	submit = SubmitField('提交')


class CommentForm(FlaskForm):
	"""
	评论
	"""
	body = TextAreaField('', validators=[DataRequired()])
	submit = SubmitField('提交')
