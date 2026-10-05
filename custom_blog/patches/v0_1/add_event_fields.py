"""Ensure the Blog Post event fields exist after a site migration."""

from custom_blog import blog_api
from custom_blog.install import create_event_fields


def execute():
	create_event_fields()
	blog_api.apply_blog_api_patch()