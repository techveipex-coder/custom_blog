"""Whitelisted REST endpoints, extended with the Blog Post event fields.

	GET /api/method/custom_blog.api.get_blog_list
	GET /api/method/custom_blog.api.get_blog_post?name=<blog post>
"""

import frappe
from frappe import _

from custom_blog import blog_api


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_blog_list(
	doctype=None,
	txt=None,
	filters=None,
	limit_start=0,
	limit_page_length=20,
	order_by=None,
):
	"""Published blog posts, including the event fields."""
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)

	get_list = blog_api.apply_blog_api_patch()

	return get_list(
		doctype,
		txt,
		filters,
		limit_start=int(limit_start or 0),
		limit_page_length=int(limit_page_length or 20),
		order_by=order_by,
	)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_blog_post(name):
	"""Single blog post detail payload, including the event fields."""
	doc = get_readable_blog_post(name)

	return blog_api.serialize_blog_post(doc)


def get_readable_blog_post(name):
	if not name:
		frappe.throw(_("Blog Post is required"), frappe.MissingError)

	if not frappe.db.exists("Blog Post", name):
		frappe.throw(_("Blog Post not found"), frappe.DoesNotExistError)

	doc = frappe.get_doc("Blog Post", name)

	if not doc.has_permission("read") and not doc.meta.allow_guest_to_view:
		frappe.throw(_("Not permitted to read this Blog Post"), frappe.PermissionError)

	if not doc.published and not can_view_unpublished():
		frappe.throw(_("Blog Post not found"), frappe.DoesNotExistError)

	return doc


def can_view_unpublished() -> bool:
	roles = set(frappe.get_roles())
	return bool(roles & {"Administrator", "System Manager", "Website Manager", "Blogger"})