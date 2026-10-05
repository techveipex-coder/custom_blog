"""Tests for the Blog Post event fields and the `can_register` API flag."""

from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

from custom_blog import blog_api
from custom_blog.custom_fields import EVENT_FIELD_DEFAULTS, EVENT_FIELDNAMES, EVENT_FIELDS


class TestEventFields(IntegrationTestCase):
	def setUp(self):
		self.fields = {field["fieldname"]: field for field in EVENT_FIELDS}

	# --- definitions ---

	def test_event_fields_are_declared(self):
		self.assertEqual(
			set(EVENT_FIELDNAMES), {"is_event", "event_date", "event_location", "is_owned_by_us"}
		)

	def test_is_event_defaults_to_unchecked(self):
		self.assertEqual(self.fields["is_event"]["fieldtype"], "Check")
		self.assertEqual(self.fields["is_event"]["label"], "Is Event")
		self.assertEqual(self.fields["is_event"]["default"], "0")

	def test_is_owned_by_us_is_visible_only_for_events(self):
		field = self.fields["is_owned_by_us"]

		self.assertEqual(field["fieldtype"], "Check")
		self.assertEqual(field["label"], "Hosted by VEIPEX")
		self.assertEqual(field["default"], "0")
		self.assertEqual(field["depends_on"], "eval:doc.is_event")

	def test_event_date_is_mandatory_only_for_events(self):
		field = self.fields["event_date"]

		self.assertEqual(field["fieldtype"], "Date")
		self.assertEqual(field["depends_on"], "eval:doc.is_event")
		self.assertEqual(field["mandatory_depends_on"], "eval:doc.is_event")

	def test_event_location_is_optional(self):
		field = self.fields["event_location"]

		self.assertEqual(field["fieldtype"], "Data")
		self.assertEqual(field["label"], "Location")
		self.assertEqual(field["depends_on"], "eval:doc.is_event")
		self.assertNotIn("mandatory_depends_on", field)

	def test_defaults_cover_every_field(self):
		self.assertEqual(set(EVENT_FIELD_DEFAULTS), set(EVENT_FIELDNAMES))

	# --- can_register ---

	def test_can_register_for_upcoming_hosted_event(self):
		event = {"is_event": 1, "is_owned_by_us": 1, "event_date": add_days(getdate(), 7)}

		self.assertEqual(blog_api.can_register(event), 1)

	def test_can_register_on_event_day(self):
		event = {"is_event": 1, "is_owned_by_us": 1, "event_date": getdate()}

		self.assertEqual(blog_api.can_register(event), 1)

	def test_can_register_false_for_past_event(self):
		event = {"is_event": 1, "is_owned_by_us": 1, "event_date": add_days(getdate(), -1)}

		self.assertEqual(blog_api.can_register(event), 0)

	def test_can_register_false_when_not_hosted_by_us(self):
		event = {"is_event": 1, "is_owned_by_us": 0, "event_date": add_days(getdate(), 7)}

		self.assertEqual(blog_api.can_register(event), 0)

	def test_can_register_false_for_regular_post(self):
		event = {"is_event": 0, "is_owned_by_us": 0, "event_date": add_days(getdate(), 7)}

		self.assertEqual(blog_api.can_register(event), 0)

	def test_can_register_false_without_event_date(self):
		event = {"is_event": 1, "is_owned_by_us": 1, "event_date": None}

		self.assertEqual(blog_api.can_register(event), 0)

	def test_can_register_accepts_string_values(self):
		event = {"is_event": "1", "is_owned_by_us": "1", "event_date": add_days(getdate(), 1)}

		self.assertEqual(blog_api.can_register(event), 1)

	# --- payload ---

	def test_event_payload_contains_derived_flag(self):
		payload = blog_api.event_payload(
			{
				"is_event": 1,
				"event_date": add_days(getdate(), 3),
				"event_location": "Bengaluru",
				"is_owned_by_us": 1,
			}
		)

		self.assertEqual(payload["is_event"], 1)
		self.assertEqual(payload["is_owned_by_us"], 1)
		self.assertEqual(payload["event_location"], "Bengaluru")
		self.assertEqual(payload["can_register"], 1)

	def test_event_payload_fills_missing_values(self):
		payload = blog_api.event_payload({})

		self.assertEqual(payload, {**EVENT_FIELD_DEFAULTS, "can_register": 0})