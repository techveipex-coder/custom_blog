app_name = "custom_blog"
app_title = "Custom Blog"
app_publisher = "Vepiex Marketing"
app_description = "Extends the blog app with event fields on Blog Post"
app_email = "admin@example.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["blog"]

# Installation
# ------------

after_install = "custom_blog.install.after_install"
before_uninstall = "custom_blog.install.before_uninstall"
before_tests = "custom_blog.install.before_tests"

# Request Events
# ----------------

# `get_blog_list` lives in the blog app, so it is patched on every request to
# make sure the event fields are part of the blog list / detail payload.
before_request = ["custom_blog.blog_api.apply_blog_api_patch"]

# Testing
# -------

# before_tests = "custom_blog.install.before_tests"