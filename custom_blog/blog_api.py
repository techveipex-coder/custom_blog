"""API layer that extends the `blog` app's serializers with the event fields.

`blog` app v16 returns the blog listing from
`blog.blog.doctype.blog_post.blog_post.get_blog_list()` (used by the website
templates through `get_list_context`) and the blog detail from the page
renderer, which does `context.update(doc.as_dict())`.

The website listing payload is built with an explicit column list, so the new
Custom Fields are missing there. `apply_blog_api_patch()` wraps that function so
every existing consumer (the `/blog` page, category pages and the templates)
gets `is_event`, `event_date` and `event_location` in the response without
touching the `blog` app.

The detail page already carries the fields because the renderer dumps the whole
document; `serialize_blog_post()` exposes the same payload over a whitelisted
REST endpoint for API consumers.
"""

import functools

import frappe
from frappe.utils import cint
from frappe.website.utils import find_first_image, get_html_content_based_on_type

from custom_blog.custom_fields import EVENT_FIELD_DEFAULTS, EVENT_FIELDNAMES

ORIGINAL_ATTR = "_custom_blog_original_get_blog_list"


def event_fields_installed() -> bool:
	"""True when all event fields are present on the Blog Post DocType."""
	meta = frappe.get_meta("Blog Post")
	return all(meta.has_field(fieldname) for fieldname in EVENT_FIELDNAMES)


def apply_blog_api_patch(*args, **kwargs):
	"""Replace `blog`'s `get_blog_list` with a wrapper that adds event fields.

	Idempotent: calling it again returns the already patched function.
	"""
	from blog.blog.doctype.blog_post import blog_post

	if getattr(blog_post.get_blog_list, ORIGINAL_ATTR, None):
		return blog_post.get_blog_list

	original = blog_post.get_blog_list
	patched = _with_event_fields(original)
	setattr(patched, ORIGINAL_ATTR, original)
	blog_post.get_blog_list = patched

	return patched


def _with_event_fields(original):
	@functools.wraps(original)
	def get_blog_list(
		doctype=None, txt=None, filters=None, limit_start=0, limit_page_length=20, order_by=None
	):
		posts = original(doctype, txt, filters, limit_start, limit_page_length, order_by)
		add_event_data(posts)
		return posts

	return get_blog_list


def add_event_data(posts):
	"""Add `is_event`, `event_date` and `event_location` to each post dict, in place."""
	if not posts or not event_fields_installed():
		return posts

	names = [post.get("name") for post in posts if post.get("name")]
	if not names:
		return posts

	try:
		rows = frappe.get_all(
			"Blog Post",
			filters={"name": ("in", names)},
			fields=["name", *EVENT_FIELDNAMES],
			as_list=True,
		)
	except Exception as e:
		# columns not created yet (field added but `updatedb` not run)
		if not frappe.db.is_missing_column(e):
			raise
		return posts

	values = {row[0]: dict(zip(EVENT_FIELDNAMES, row[1:])) for row in rows}

	for post in posts:
		data = values.get(post.get("name")) or EVENT_FIELD_DEFAULTS
		post.update(
			{
				"is_event": cint(data["is_event"]),
				"event_date": data["event_date"],
				"event_location": data["event_location"] or None,
			}
		)

	return posts


def serialize_blog_post(doc=None, name=None) -> dict:
	"""Detail payload for a single Blog Post, matching the list serializer."""
	if doc is None:
		doc = frappe.get_doc("Blog Post", name)

	content = get_html_content_based_on_type(doc, "content", doc.content_type)

	data = {
		"name": doc.name,
		"title": doc.title,
		"route": doc.route,
		"blog_category": doc.blog_category,
		"blogger": doc.blogger,
		"published_on": doc.published_on,
		"read_time": getattr(doc, "read_time", None),
		"featured": cint(doc.featured),
		"cover_image": doc.meta_image or find_first_image(content),
		"content": content,
		"content_type": doc.content_type,
		"blog_intro": doc.blog_intro,
		"meta_title": getattr(doc, "meta_title", None),
		"meta_description": getattr(doc, "meta_description", None),
		"disable_comments": cint(doc.disable_comments),
		"disable_likes": cint(doc.disable_likes),
	}

	data.update(event_data(doc))

	data["category"] = frappe.db.get_value(
		"Blog Category", doc.blog_category, ["name", "route", "title"], as_dict=True
	)
	data["author"] = get_author(doc.blogger)

	return data


def event_data(doc) -> dict:
	"""Event fields of a document, with safe defaults when not installed."""
	if not event_fields_installed():
		return dict(EVENT_FIELD_DEFAULTS)

	return {
		"is_event": cint(doc.get("is_event")),
		"event_date": doc.get("event_date"),
		"event_location": doc.get("event_location") or None,
	}


def get_author(blogger):
	if not blogger:
		return {}

	author = frappe.db.get_value("Blogger", blogger, ["name", "full_name", "avatar"], as_dict=True)
	if not author:
		return {}

	if author.avatar and not author.avatar.startswith(("http://", "https://", "/")):
		author.avatar = "/" + author.avatar

	return author