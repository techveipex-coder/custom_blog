"""Tests for `Blog Event Signup` and the public event registration endpoint."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, get_datetime, getdate

from custom_blog import api, blog_api

GUEST = {"full_name": "Asha Rao", "email": "asha@example.com", "phone": "+91 98450 00001"}


class TestBlogEventSignup(IntegrationTestCase):
	def setUp(self):
		if "blog" not in frappe.get_installed_apps():
			self.skipTest("blog app is not installed on this site")

		self.blogger = frappe.get_doc({"doctype": "Blogger", "full_name": "Test Blogger"}).insert(
			ignore_permissions=True
		)
		self.category = frappe.get_doc(
			{"doctype": "Blog Category", "title": "Test Category"}
		).insert(ignore_permissions=True)

	def make_event(self, event_date=None, is_owned_by_us=1, is_event=1):
		post = frappe.get_doc(
			{
				"doctype": "Blog Post",
				"title": f"Test Event {frappe.generate_hash(length=6)}",
				"blog_category": self.category.name,
				"blogger": self.blogger.name,
				"content": "<p>Come along</p>",
				"published": 1,
				"allow_guest_to_view": 1,
				"is_event": is_event,
				"is_owned_by_us": is_owned_by_us,
				"event_date": event_date,
				"event_location": "Bengaluru",
			}
		).insert(ignore_permissions=True)

		return post

	def register(self, post, **overrides):
		details = {**GUEST, "blog_post": post.name, **overrides}

		frappe.set_user("Guest")
		try:
			return api.register_for_event(**details)
		finally:
			frappe.set_user("Administrator")

	# --- registration ---

	def test_register_returns_success(self):
		post = self.make_event(add_days(getdate(), 7))
		response = self.register(post)

		self.assertTrue(response["success"])
		self.assertFalse(response["already_registered"])
		self.assertEqual(response["blog_post"], post.name)
		self.assertIn(post.title, response["message"])

		signup = frappe.get_last_doc("Blog Event Signup")
		self.assertEqual(signup.blog_post, post.name)
		self.assertEqual(signup.full_name, GUEST["full_name"])
		self.assertEqual(signup.email, GUEST["email"])
		self.assertTrue(signup.registered_on)

	def test_register_normalizes_email_case_and_whitespace(self):
		post = self.make_event(add_days(getdate(), 7))
		self.register(post, email="  ASHA@Example.COM ")

		self.assertEqual(frappe.get_last_doc("Blog Event Signup").email, "asha@example.com")

	def test_duplicate_signup_is_not_an_error(self):
		post = self.make_event(add_days(getdate(), 7))
		self.register(post)

		response = self.register(post)

		self.assertTrue(response["success"])
		self.assertTrue(response["already_registered"])
		self.assertEqual(response["message"], "You're already registered for this event")
		self.assertEqual(api.get_event_signup_count(post.name), 1)

	def test_duplicate_is_case_insensitive(self):
		post = self.make_event(add_days(getdate(), 7))
		self.register(post)
		self.register(post, email="ASHA@example.com")

		self.assertEqual(api.get_event_signup_count(post.name), 1)

	def test_register_rejects_missing_blog_post(self):
		self.assertRaises(
			frappe.DoesNotExistError,
			api.register_for_event,
			blog_post="no-such-post",
			**GUEST,
		)

	def test_register_rejects_regular_post(self):
		post = self.make_event(is_event=0, is_owned_by_us=0)

		with self.assertRaises(frappe.ValidationError) as ctx:
			self.register(post)

		self.assertIn("isn't an event we're hosting", str(ctx.exception))

	def test_register_rejects_event_not_hosted_by_us(self):
		post = self.make_event(add_days(getdate(), 7), is_owned_by_us=0)

		with self.assertRaises(frappe.ValidationError) as ctx:
			self.register(post)

		self.assertIn("isn't an event we're hosting", str(ctx.exception))

	def test_register_rejects_event_without_date(self):
		post = self.make_event(event_date=None)

		with self.assertRaises(frappe.ValidationError) as ctx:
			self.register(post)

		self.assertIn("no date set", str(ctx.exception))

	def test_register_rejects_past_event(self):
		post = self.make_event(add_days(getdate(), -1))

		with self.assertRaises(frappe.ValidationError) as ctx:
			self.register(post)

		self.assertIn("Registration for this event has closed", str(ctx.exception))
		self.assertFalse(frappe.db.exists("Blog Event Signup", {"blog_post": post.name}))

	def test_register_accepts_event_today(self):
		"""An event dated today is still registrable while it has not happened yet."""
		post = self.make_event(getdate())

		self.assertTrue(self.register(post)["success"])

	def test_register_rejects_blank_details(self):
		post = self.make_event(add_days(getdate(), 7))

		with self.assertRaises(frappe.MissingError) as ctx:
			self.register(post, full_name="  ", phone="")

		self.assertIn("Full Name", str(ctx.exception))
		self.assertIn("Phone", str(ctx.exception))

	def test_register_rejects_invalid_email(self):
		post = self.make_event(add_days(getdate(), 7))

		with self.assertRaises(frappe.ValidationError):
			self.register(post, email="not-an-email")

		self.assertFalse(frappe.db.exists("Blog Event Signup", {"blog_post": post.name}))

	def test_register_rejects_unpublished_post(self):
		post = self.make_event(add_days(getdate(), 7))
		post.published = 0
		post.allow_guest_to_view = 0
		post.save()

		frappe.set_user("Guest")
		try:
			self.assertRaises(
				frappe.PermissionError,
				api.register_for_event,
				blog_post=post.name,
				**GUEST,
			)
		finally:
			frappe.set_user("Administrator")

	# --- signup count ---

	def test_signup_count_is_zero_for_unknown_event(self):
		post = self.make_event(add_days(getdate(), 7))

		self.assertEqual(api.get_event_signup_count(post.name), 0)

	def test_signup_count_counts_each_signup(self):
		post = self.make_event(add_days(getdate(), 7))
		self.register(post)
		self.register(post, email="ravi@example.com")

		self.assertEqual(api.get_event_signup_count(post.name), 2)

	def test_signup_count_requires_blog_post(self):
		self.assertRaises(frappe.MissingError, api.get_event_signup_count, "")

	# --- doctype ---

	def test_signup_defaults_registered_on(self):
		post = self.make_event(add_days(getdate(), 7))
		before = get_datetime()
		self.register(post)

		signup = frappe.get_last_doc("Blog Event Signup")

		self.assertGreaterEqual(signup.get("registered_on"), before)

	def test_signup_validates_email_format(self):
		post = self.make_event(add_days(getdate(), 7))
		signup = frappe.get_doc(
			{"doctype": "Blog Event Signup", "blog_post": post.name, **GUEST}
		)
		signup.email = "nope"

		self.assertRaises(frappe.ValidationError, signup.insert)

	def test_signup_doctype_blocks_duplicate(self):
		post = self.make_event(add_days(getdate(), 7))
		fields = {"doctype": "Blog Event Signup", "blog_post": post.name, **GUEST}

		frappe.get_doc(fields).insert(ignore_permissions=True)

		self.assertRaises(
			frappe.DuplicateEntryError,
			frappe.get_doc(fields).insert,
			ignore_permissions=True,
		)

	def test_signup_requires_blog_post(self):
		signup = frappe.get_doc({"doctype": "Blog Event Signup", **GUEST})

		self.assertRaises(frappe.ValidationError, signup.insert)

	def test_signup_requires_all_details(self):
		post = self.make_event(add_days(getdate(), 7))
		signup = frappe.get_doc(
			{"doctype": "Blog Event Signup", "blog_post": post.name, "full_name": "Asha"}
		)

		self.assertRaises(frappe.ValidationError, signup.insert)


class TestRegistrationBlocker(IntegrationTestCase):
	"""`registration_blocker` and `can_register` must never disagree."""

	def test_blocker_matches_can_register(self):
		hosted = {"is_event": 1, "is_owned_by_us": 1}
		future = add_days(getdate(), 7)
		past = add_days(getdate(), -1)

		cases = (
			{**hosted, "event_date": future},
			{**hosted, "event_date": getdate()},
			{**hosted, "event_date": past},
			{**hosted, "event_date": None},
			{"is_event": 0, "is_owned_by_us": 0, "event_date": future},
			{"is_event": 1, "is_owned_by_us": 0, "event_date": future},
			{},
		)

		for event in cases:
			with self.subTest(event=event):
				blocker = blog_api.registration_blocker(event)

				self.assertEqual(blog_api.can_register(event), int(blocker is None))

	def test_blocker_messages_are_distinct(self):
		hosted = {"is_event": 1, "is_owned_by_us": 1}

		messages = {
			blog_api.registration_blocker({**hosted, "event_date": add_days(getdate(), 7)}),
			blog_api.registration_blocker({**hosted, "event_date": add_days(getdate(), -1)}),
			blog_api.registration_blocker({**hosted, "event_date": None}),
			blog_api.registration_blocker({}),
		}

		self.assertEqual(len(messages - {None}), 3)