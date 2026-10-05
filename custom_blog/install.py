import frappe
from frappe.custom.doctype.custom_field.custom_field import (
	create_custom_fields,
	delete_custom_fields,
)
from frappe.website.utils import clear_cache

from custom_blog import blog_api
from custom_blog.custom_fields import CUSTOM_FIELDS


def after_install():
	create_event_fields()


def before_uninstall():
	delete_event_fields()


def before_tests():
	# tests may run against a site installed before the patch was applied
	create_event_fields()
	blog_api.apply_blog_api_patch()


def create_event_fields():
	"""Add the event fields to Blog Post and run updatedb for them."""
	if "blog" not in frappe.get_installed_apps():
		return

	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
	reset_cache()


def delete_event_fields():
	if "blog" not in frappe.get_installed_apps():
		return

	delete_custom_fields(CUSTOM_FIELDS)
	reset_cache()


def reset_cache():
	"""Drop the DocType cache and the cached website html of the blog pages."""
	frappe.clear_cache(doctype="Blog Post")
	frappe.clear_cache(doctype="Custom Field")
	clear_cache()