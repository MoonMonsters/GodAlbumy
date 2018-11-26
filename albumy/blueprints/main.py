# -*- coding: utf-8 -*-
"""
主要功能模块
"""
import os

from flask import (
	render_template,
	flash,
	redirect,
	url_for,
	current_app,
	send_from_directory,
	request,
	abort,
	Blueprint,
)
from flask_login import login_required, current_user
from sqlalchemy.sql.expression import func

from albumy.decorators import confirm_required, permission_required
from albumy.extensions import db
from albumy.forms.main import DescriptionForm, TagForm, CommentForm
from albumy.models import User, Photo, Tag, Follow, Collect, Comment, Notification
from albumy.notifications import push_comment_notification, push_collect_notification
from albumy.utils import rename_image, resize_image, redirect_back, flash_errors, logger

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
	"""
	主页
	"""
	logger.info('url = ' + str(request.url))
	logger.info('当前用户是否登录: ' + str(current_user.is_authenticated))
	# 在主页页面，登录用户和未登录用户显示的是不一致的
	# 如果登录了，就会按时间顺序显示自己和关注的用户的发布的图片
	# 而如果没有登录，则显示主页图片以及注册功能
	if current_user.is_authenticated:
		# 页码
		page = request.args.get("page", 1, type=int)
		# 每一页的图片多少
		per_page = current_app.config["ALBUMY_PHOTO_PER_PAGE"]
		pagination = (
			# 关联Follow表，关联条件是Follow的followed_id和Photo的authid_id一致
			Photo.query.join(Follow, Follow.followed_id == Photo.author_id)
				# 过滤出自己关注的对象
				.filter(Follow.follower_id == current_user.id)
				# 按时间顺序排序
				.order_by(Photo.timestamp.desc()).paginate(page, per_page)
		)
		# 得到photo集合
		photos = pagination.items
	else:
		pagination = None
		photos = None
	tags = (
		Tag.query.join(Tag.photos)
			.group_by(Tag.id)
			.order_by(func.count(Photo.id).desc())
			.limit(10)
	)
	return render_template(
		"main/index.html",
		pagination=pagination,
		photos=photos,
		tags=tags,
		Collect=Collect,
	)


@main_bp.route("/explore")
def explore():
	"""
	发现，随机给出12张图片
	"""
	logger.info('url = ' + str(request.url))
	photos = Photo.query.order_by(func.random()).limit(12)
	return render_template("main/explore.html", photos=photos)


@main_bp.route("/search")
def search():
	"""
	搜索
	"""
	logger.info('url = ' + str(request.url))
	# 搜索条件
	q = request.args.get("q", "")
	# 搜索条件为空，直接返回
	if q == "":
		flash("请输入搜索条件！", "warning")
		return redirect_back()
	logger.info('搜索内容，q = ' + str(q))
	# 搜索类型，默认是photo
	# 在search.html页面，通过切换侧边栏来得到不同的category
	category = request.args.get("category", "photo")
	logger.info('搜索选项，category = ' + str(category))
	page = request.args.get("page", 1, type=int)
	per_page = current_app.config["ALBUMY_SEARCH_RESULT_PER_PAGE"]
	# 搜索用户
	# 使用whooshee_search，会搜索在model中定义的属性
	# 例如，就会在User中搜索name和username
	if category == "user":
		pagination = User.query.whooshee_search(q).paginate(page, per_page)
	# 搜索标签
	elif category == "tag":
		pagination = Tag.query.whooshee_search(q).paginate(page, per_page)
	# 搜索图片
	else:
		pagination = Photo.query.whooshee_search(q).paginate(page, per_page)
	results = pagination.items
	return render_template(
		"main/search.html",
		q=q,
		results=results,
		pagination=pagination,
		category=category,
	)


@main_bp.route("/notifications")
@login_required
def show_notifications():
	"""
	显示消息
	"""
	logger.info('url = ' + str(request.url))
	page = request.args.get("page", 1, type=int)
	per_page = current_app.config["ALBUMY_NOTIFICATION_PER_PAGE"]
	notifications = Notification.query.with_parent(current_user)
	# None
	filter_rule = request.args.get("filter")
	logger.info('显示通知过滤规则，filter_rule = ' + str(filter_rule))
	# 未读消息
	if filter_rule == "unread":
		notifications = notifications.filter_by(is_read=False)

	# 时间排序
	pagination = notifications.order_by(Notification.timestamp.desc()).paginate(
		page, per_page
	)
	notifications = pagination.items
	return render_template(
		"main/notifications.html", pagination=pagination, notifications=notifications
	)


@main_bp.route("/notification/read/<int:notification_id>", methods=["POST"])
@login_required
def read_notification(notification_id):
	"""
	已读提醒消息
	:param notification_id: 提醒消息id
	:return:
	"""
	logger.info('url = ' + str(request.url))
	notification = Notification.query.get_or_404(notification_id)
	# 如果登录用户和消息接收者不一致，就抛出403错误
	if current_user != notification.receiver:
		abort(403)
	# 已读消息
	notification.is_read = True
	db.session.commit()
	flash("提醒消息已读！", "success")
	return redirect(url_for(".show_notifications"))


@main_bp.route("/notifications/read/all", methods=["POST"])
@login_required
def read_all_notification():
	"""
	一键已读所有消息
	"""
	logger.info('url = ' + str(request.url))
	# 遍历登录用户的所有消息
	for notification in current_user.notifications:
		# 设置为True
		notification.is_read = True
	db.session.commit()
	flash("所有消息已读！", "success")
	return redirect(url_for(".show_notifications"))


@main_bp.route("/uploads/<path:filename>")
def get_image(filename):
	"""
	获取图片
	:param filename: 图片名字
	:return: 返回图片的url
	"""
	logger.info('url = ' + str(request.url))
	logger.info('获取图片的名称，filename = ' + str(filename))
	return send_from_directory(current_app.config["ALBUMY_UPLOAD_PATH"], filename)


@main_bp.route("/avatars/<path:filename>")
def get_avatar(filename):
	"""
	获取头像
	:param filename: 头像名字
	"""
	logger.info('获取头像的名称，filename = ' + str(filename))
	return send_from_directory(current_app.config["AVATARS_SAVE_PATH"], filename)


@main_bp.route("/upload", methods=["GET", "POST"])
@login_required
@confirm_required
@permission_required("UPLOAD")
def upload():
	"""
	上传图片
	"""
	logger.info('url = ' + str(request.url))
	if request.method == "POST" and "file" in request.files:
		# 文件对象
		f = request.files.get("file")
		# 文件名
		filename = rename_image(f.filename)
		# 保存
		f.save(os.path.join(current_app.config["ALBUMY_UPLOAD_PATH"], filename))
		# 小图
		# 在resize_image函数中，会保存图片
		filename_s = resize_image(
			f, filename, current_app.config["ALBUMY_PHOTO_SIZE"]["small"]
		)
		# 中图
		filename_m = resize_image(
			f, filename, current_app.config["ALBUMY_PHOTO_SIZE"]["medium"]
		)
		# 保存图片对象
		photo = Photo(
			filename=filename,
			filename_s=filename_s,
			filename_m=filename_m,
			author=current_user._get_current_object(),
		)
		logger.info('上传文件，{},{},{}'.format(filename, filename_m, filename_s))
		# 提交
		db.session.add(photo)
		db.session.commit()
	return render_template("main/upload.html")


@main_bp.route("/photo/<int:photo_id>")
def show_photo(photo_id):
	"""
	显示图片详细信息
	:param photo_id: 图片id
	"""
	logger.info('url = ' + str(request.url))
	photo = Photo.query.get_or_404(photo_id)
	page = request.args.get("page", 1, type=int)
	per_page = current_app.config["ALBUMY_COMMENT_PER_PAGE"]
	# 获取该图片下的所有评论
	pagination = (
		Comment.query.with_parent(photo)
			.order_by(Comment.timestamp.asc())
			.paginate(page, per_page)
	)
	comments = pagination.items

	comment_form = CommentForm()
	# 描述
	description_form = DescriptionForm()
	# 标签
	tag_form = TagForm()

	description_form.description.data = photo.description
	return render_template(
		"main/photo.html",
		photo=photo,
		comment_form=comment_form,
		description_form=description_form,
		tag_form=tag_form,
		pagination=pagination,
		comments=comments,
	)


@main_bp.route("/photo/n/<int:photo_id>")
def photo_next(photo_id):
	"""
	下一张图片
	:param photo_id: 图片id
	"""
	logger.info('url = ' + str(request.url))
	photo = Photo.query.get_or_404(photo_id)
	photo_n = (
		# 考虑到会删除图片，图片的id不是连续的，所以不能使用id+1的方式得到下一张图片
		# 得到大于现在图片的id的最新一张
		Photo.query.with_parent(photo.author)
			.filter(Photo.id < photo_id)
			.order_by(Photo.id.desc())
			.first()
	)

	if photo_n is None:
		flash("已经是最后一张图片了！", "info")
		return redirect(url_for(".show_photo", photo_id=photo_id))
	return redirect(url_for(".show_photo", photo_id=photo_n.id))


@main_bp.route("/photo/p/<int:photo_id>")
def photo_previous(photo_id):
	"""
	得到上一张图片
	:param photo_id: 图片id
	"""
	logger.info('url = ' + str(request.url))
	photo = Photo.query.get_or_404(photo_id)
	photo_p = (
		Photo.query.with_parent(photo.author)
			.filter(Photo.id > photo_id)
			.order_by(Photo.id.asc())
			.first()
	)

	if photo_p is None:
		flash("已经是第一张图片了！", "info")
		return redirect(url_for(".show_photo", photo_id=photo_id))
	return redirect(url_for(".show_photo", photo_id=photo_p.id))


@main_bp.route("/collect/<int:photo_id>", methods=["POST"])
@login_required
@confirm_required
@permission_required("COLLECT")
def collect(photo_id):
	"""
	收藏图片
	:param photo_id: 图片id
	"""
	logger.info('url = ' + str(request.url))
	logger.info('收藏者的用户名: {}，收藏的图片ID: {}'.format(current_user.username, photo_id))
	photo = Photo.query.get_or_404(photo_id)
	# 调用User的is_collecting函数，判断是否已经收藏过该图片
	if current_user.is_collecting(photo):
		flash("该图片已经收藏过了！", "info")
		return redirect(url_for(".show_photo", photo_id=photo_id))
	# 收藏图片
	current_user.collect(photo)
	flash("收藏成功！", "success")
	# 根据判断条件，是否需要发出提醒消息
	if current_user != photo.author and photo.author.receive_collect_notification:
		push_collect_notification(
			collector=current_user, photo_id=photo_id, receiver=photo.author
		)
	return redirect(url_for(".show_photo", photo_id=photo_id))


@main_bp.route("/uncollect/<int:photo_id>", methods=["POST"])
@login_required
def uncollect(photo_id):
	"""
	取消收藏
	:param photo_id: 图片id
	"""
	logger.info('url = ' + str(request.url))
	logger.info('取消收藏的用户名: {}，图片ID: {}'.format(current_user.username, photo_id))
	photo = Photo.query.get_or_404(photo_id)
	# 如果没有收藏图片，则直接返回
	if not current_user.is_collecting(photo):
		flash("没有收藏过该图片，无法取消！", "info")
		return redirect(url_for("main.show_photo", photo_id=photo_id))
	# 取消收藏
	current_user.uncollect(photo)
	flash("取消收藏成功！", "info")
	return redirect(url_for(".show_photo", photo_id=photo_id))


@main_bp.route("/report/comment/<int:comment_id>", methods=["POST"])
@login_required
@confirm_required
def report_comment(comment_id):
	"""
	举报评论
	:param comment_id: 评论id
	"""
	logger.info('url = ' + str(request.url))
	logger.info('举报者的用户名: {}，被举报评论ID: {}'.format(current_user.username, comment_id))
	comment = Comment.query.get_or_404(comment_id)
	# 评论的举报数+1
	comment.flag += 1
	logger.info('该评论的被举报次数: ' + str(comment.flag))
	db.session.commit()
	flash("举报评论成功！", "success")
	return redirect(url_for(".show_photo", photo_id=comment.photo_id))


@main_bp.route("/report/photo/<int:photo_id>", methods=["POST"])
@login_required
@confirm_required
def report_photo(photo_id):
	"""
	举报图片
	:param photo_id: 图片id
	"""
	logger.info('url = ' + str(request.url))
	photo = Photo.query.get_or_404(photo_id)
	# 图片的举报数+1
	photo.flag += 1
	logger.info('该图片被举报的次数: ' + str(photo.flag))
	db.session.commit()
	flash("图片举报成功！", "success")
	return redirect(url_for(".show_photo", photo_id=photo.id))


@main_bp.route("/photo/<int:photo_id>/collectors")
def show_collectors(photo_id):
	"""
	显示所有收藏该图片的用户
	:param photo_id: 图片id
	"""
	logger.info('url = ' + str(request.url))
	photo = Photo.query.get_or_404(photo_id)
	page = request.args.get("page", 1, type=int)
	per_page = current_app.config["ALBUMY_USER_PER_PAGE"]
	pagination = (
		Collect.query.with_parent(photo)
			.order_by(Collect.timestamp.asc())
			.paginate(page, per_page)
	)
	collects = pagination.items
	return render_template(
		"main/collectors.html", collects=collects, photo=photo, pagination=pagination
	)


@main_bp.route("/photo/<int:photo_id>/description", methods=["POST"])
@login_required
def edit_description(photo_id):
	"""
	编辑图片描述
	:param photo_id: 图片id
	"""
	logger.info('url = ' + str(request.url))
	photo = Photo.query.get_or_404(photo_id)
	if current_user != photo.author and not current_user.can("MODERATE"):
		abort(403)

	form = DescriptionForm()
	if form.validate_on_submit():
		photo.description = form.description.data
		logger.info('修改了图片id={}的描述={}'.format(photo_id, photo.description))
		db.session.commit()
		flash("描述更新成功！", "success")

	flash_errors(form)
	return redirect(url_for(".show_photo", photo_id=photo_id))


@main_bp.route("/photo/<int:photo_id>/comment/new", methods=["POST"])
@login_required
@permission_required("COMMENT")
def new_comment(photo_id):
	"""
	新的评论
	:param photo_id: 图片id
	"""
	logger.info('url = ' + str(request.url))
	photo = Photo.query.get_or_404(photo_id)
	page = request.args.get("page", 1, type=int)
	form = CommentForm()
	if form.validate_on_submit():
		body = form.body.data
		author = current_user._get_current_object()
		comment = Comment(body=body, author=author, photo=photo)
		logger.info('用户:{}对图片:{}发表了评论:{}'.format(current_user.username, photo_id, body))
		# 被回复的用户
		replied_id = request.args.get("reply")
		if replied_id:
			comment.replied = Comment.query.get_or_404(replied_id)
			if comment.replied.author.receive_comment_notification:
				push_comment_notification(
					photo_id=photo.id, receiver=comment.replied.author
				)
		db.session.add(comment)
		db.session.commit()
		flash("评论成功！", "success")

		if current_user != photo.author and photo.author.receive_comment_notification:
			push_comment_notification(photo_id, receiver=photo.author, page=page)

	flash_errors(form)
	return redirect(url_for(".show_photo", photo_id=photo_id, page=page))


@main_bp.route("/photo/<int:photo_id>/tag/new", methods=["POST"])
@login_required
def new_tag(photo_id):
	"""
	新标签
	:param photo_id: 图片id
	"""
	logger.info('url = ' + str(request.url))
	photo = Photo.query.get_or_404(photo_id)
	if current_user != photo.author and not current_user.can("MODERATE"):
		abort(403)

	form = TagForm()
	if form.validate_on_submit():
		# 添加新标签时，如果有多个标签，会以空格隔开
		for name in form.tag.data.split():
			# 查询，判断标签是否已经存在
			tag = Tag.query.filter_by(name=name).first()
			# 如果不存在，则先创建标签
			if tag is None:
				tag = Tag(name=name)
				logger.debug('用户:{}添加了新标签:{}'.format(current_user.username, name))
				db.session.add(tag)
				db.session.commit()
			# 将标签加入到photo的标签中
			if tag not in photo.tags:
				photo.tags.append(tag)
				db.session.commit()
		flash("标签添加成功！", "success")

	flash_errors(form)
	return redirect(url_for(".show_photo", photo_id=photo_id))


@main_bp.route("/set-comment/<int:photo_id>", methods=["POST"])
@login_required
def set_comment(photo_id):
	"""
	设置该图片是否可以被其他用户评论
	:param photo_id: 图片id
	"""
	logger.info('url = ' + str(request.url))
	photo = Photo.query.get_or_404(photo_id)
	if current_user != photo.author:
		abort(403)

	if photo.can_comment:
		photo.can_comment = False
		flash("评论已关闭！", "info")
	else:
		photo.can_comment = True
		flash("评论已打开！", "info")
	db.session.commit()
	return redirect(url_for(".show_photo", photo_id=photo_id))


@main_bp.route("/reply/comment/<int:comment_id>")
@login_required
@permission_required("COMMENT")
def reply_comment(comment_id):
	"""
	回复评论
	:param comment_id: 被回复的评论id
	"""
	logger.info('url = ' + str(request.url))
	comment = Comment.query.get_or_404(comment_id)
	return redirect(
		url_for(
			".show_photo",
			photo_id=comment.photo_id,
			reply=comment_id,
			author=comment.author.name,
		)
		+ "#comment-form"
	)


@main_bp.route("/delete/photo/<int:photo_id>", methods=["POST"])
@login_required
def delete_photo(photo_id):
	"""
	删除图片
	:param photo_id: 图片id
	"""
	logger.info('url = ' + str(request.url))
	photo = Photo.query.get_or_404(photo_id)
	# 如果执行删除操作的用户不是图片的作者，无法删除
	# 如果没有管理权限，无法删除
	if current_user != photo.author and not current_user.can("MODERATE"):
		abort(403)

	db.session.delete(photo)
	db.session.commit()
	flash("图片已删除！", "info")

	# 下一张图片
	photo_n = (
		Photo.query.with_parent(photo.author)
			.filter(Photo.id < photo_id)
			.order_by(Photo.id.desc())
			.first()
	)
	# 上一张图片
	if photo_n is None:
		photo_p = (
			Photo.query.with_parent(photo.author)
				.filter(Photo.id > photo_id)
				.order_by(Photo.id.asc())
				.first()
		)
		# 如果没有其他图片了，返回用户主页
		if photo_p is None:
			return redirect(url_for("user.index", username=photo.author.username))
		return redirect(url_for(".show_photo", photo_id=photo_p.id))
	return redirect(url_for(".show_photo", photo_id=photo_n.id))


@main_bp.route("/delete/comment/<int:comment_id>", methods=["POST"])
@login_required
def delete_comment(comment_id):
	"""
	删除评论
	:param comment_id: 评论id
	"""
	logger.info('url = ' + str(request.url))
	comment = Comment.query.get_or_404(comment_id)
	# 评论作者可以删除
	# 图片作者可以删除
	# 管理权限的人可以删除
	if (
			current_user != comment.author
			and current_user != comment.photo.author
			and not current_user.can("MODERATE")
	):
		abort(403)
	db.session.delete(comment)
	logger.info('用户:{}删除了评论:{}'.format(current_user.username, comment.body))
	db.session.commit()
	flash("评论删除成功！", "info")
	return redirect(url_for(".show_photo", photo_id=comment.photo_id))


@main_bp.route("/tag/<int:tag_id>", defaults={"order": "by_time"})
@main_bp.route("/tag/<int:tag_id>/<order>")
def show_tag(tag_id, order):
	"""
	显示标签下的所有图片
	:param tag_id: 标签id
	:param order: 排序规则
	"""
	logger.info('url = ' + str(request.url))
	# 标签
	tag = Tag.query.get_or_404(tag_id)
	page = request.args.get("page", 1, type=int)
	per_page = current_app.config["ALBUMY_PHOTO_PER_PAGE"]
	# 规则
	order_rule = "time"
	# 所有图片
	pagination = (
		Photo.query.with_parent(tag)
			.order_by(Photo.timestamp.desc())
			.paginate(page, per_page)
	)
	photos = pagination.items

	# 根据收藏人数排序
	if order == "by_collects":
		photos.sort(key=lambda x: len(x.collectors), reverse=True)
		order_rule = "collects"
	return render_template(
		"main/tag.html",
		tag=tag,
		pagination=pagination,
		photos=photos,
		order_rule=order_rule,
	)


@main_bp.route("/delete/tag/<int:photo_id>/<int:tag_id>", methods=["POST"])
@login_required
def delete_tag(photo_id, tag_id):
	"""
	删除标签
	:param photo_id: 图片id
	:param tag_id: 标签id
	"""
	logger.info('url = ' + str(request.url))
	tag = Tag.query.get_or_404(tag_id)
	photo = Photo.query.get_or_404(photo_id)
	if current_user != photo.author and not current_user.can("MODERATE"):
		abort(403)
	# 从图片中移除标签
	photo.tags.remove(tag)
	db.session.commit()

	# 如果该标签下没有图片了，删除标签
	if not tag.photos:
		db.session.delete(tag)
		logger.info('用户:{}删除了标签:{}'.format(current_user.username, tag.name))
		db.session.commit()

	flash("标签已删除！", "info")
	return redirect(url_for(".show_photo", photo_id=photo_id))
