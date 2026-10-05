"""Whitelisted REST endpoints, extended with the Blog Post event fields.

	GET /api/method/custom_blog.api.get_blog_list
	GET /api/method/custom_blog.api.get_blog_post?name=<blog post>
	POST /api/method/custom_blog.api.register_for_event
	GET /api/method/custom_blog.api.get_event_signup_count?blog_post=<blog post>
"""

import frappe
from frappe import _
from frappe.utils import validate_email_address

from custom_blog import blog_api

#: labels of the fields collected by `register_for_event`, translated at throw time
SIGNUP_FIELD_LABELS = {"full_name": "Full Name", "email": "Email", "phone": "Phone"}


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


@frappe.whitelist(allow_guest=True, methods=["POST"])
def register_for_event(blog_post, full_name, email, phone):
	"""Register a guest for an event Blog Post hosted by us.

	Re-runs the `can_register` rules server-side — the flag sent by the frontend
	is only a hint for showing the button, never the authority to accept a signup.

	Returns `{"success": true, "message": ...}`. A guest who is already registered
	also gets `success: true` (plus `already_registered`) instead of an error, since
	their intent is already satisfied.
	"""
	doc = get_readable_blog_post(blog_post)

	blocker = blog_api.registration_blocker(blog_api.event_data(doc))
	if blocker:
		frappe.throw(blocker, frappe.ValidationError)

	details = validate_signup_details(full_name, email, phone)

	duplicate = frappe.db.exists(
		"Blog Event Signup", {"blog_post": doc.name, "email": details["email"]}
	)
	if duplicate:
		return {
			"success": True,
			"already_registered": True,
			"blog_post": doc.name,
			"message": _("You're already registered for this event"),
		}

	# no role holds insert permission on Blog Event Signup, the checks above stand in
	# for it
	frappe.get_doc({"doctype": "Blog Event Signup", "blog_post": doc.name, **details}).insert(
		ignore_permissions=True
	)

	return {
		"success": True,
		"already_registered": False,
		"blog_post": doc.name,
		"can_register": 1,
		"message": _("You're registered for {0}. See you there!").format(doc.title),
	}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_event_signup_count(blog_post):
	"""How many people are registered for an event, for "X people are attending"."""
	if not blog_post:
		frappe.throw(_("Blog Post is required"), frappe.MissingError)

	if not frappe.db.exists("Blog Post", blog_post):
		frappe.throw(_("Blog Post not found"), frappe.DoesNotExistError)

	return frappe.db.count("Blog Event Signup", {"blog_post": blog_post})


def validate_signup_details(full_name, email, phone) -> dict:
	"""Clean up and validate the guest supplied details.

	Returns them ready to be merged into a Blog Event Signup; throws a single
	`Missing Error` listing everything that is absent, so a guest filling in a
	form is not shown one error per field.
	"""
	details = {
		"full_name": (full_name or "").strip(),
		"email": (email or "").strip().lower(),
		"phone": (phone or "").strip(),
	}

	missing = [_(SIGNUP_FIELD_LABELS[field]) for field, value in details.items() if not value]
	if missing:
		frappe.throw(_("Please fill in {0}").format(", ".join(missing)), frappe.MissingError)

	validate_email_address(details["email"], throw=True)

	return details