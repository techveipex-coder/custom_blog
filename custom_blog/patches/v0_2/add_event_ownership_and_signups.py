"""Add `is_owned_by_us` to Blog Post and register the Blog Event Signup DocType.

`v0_1.add_event_fields` is recorded in the Patch Log, so a site that already
migrated never runs it again and would never pick up fields added afterwards.
This patch re-runs the (idempotent) field setup, and runs in `post_model_sync` so
the `Blog Event Signup` table already exists.
"""

from custom_blog import blog_api
from custom_blog.install import create_event_fields


def execute():
	create_event_fields()
	blog_api.apply_blog_api_patch()