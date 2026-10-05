import frappe
from frappe import _
from frappe.model.document import Document


class BlogEventSignup(Document):
	"""A guest registration for an event `Blog Post` hosted by us.

	Rows are created by `custom_blog.api.register_for_event`, which does the
	registrability checks and inserts with `ignore_permissions=True`; no role is
	granted insert permission on this DocType, so guests cannot post signups
	through the generic API.
	"""

	def validate(self):
		self.full_name = (self.full_name or "").strip()
		self.email = (self.email or "").strip().lower()
		self.phone = (self.phone or "").strip()
		self.check_duplicate()

	def check_duplicate(self):
		"""Backstop against duplicate signups for the same event.

		The public API answers duplicates with a friendly message before it gets
		here; this covers direct desk/import writes and races.
		"""
		if not (self.blog_post and self.email):
			return

		duplicate = frappe.db.exists(
			"Blog Event Signup", {"blog_post": self.blog_post, "email": self.email}
		)

		if duplicate and duplicate != self.name:
			frappe.throw(_("You're already registered for this event"), frappe.DuplicateEntryError)