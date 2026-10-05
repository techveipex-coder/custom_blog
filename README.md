# Custom Blog

Extension app for the `blog` app (Frappe/ERPNext **v16**). It adds **event** support to
`Blog Post` without editing the `blog` app itself.

## What it does

### 1. Blog Post fields

Three fields are added to `Blog Post` as Custom Fields (`is_event` section, collapsible):

| Field | Type | Label | Rules |
| --- | --- | --- | --- |
| `is_event` | Check | Is Event | default `0` |
| `event_date` | Date | Event Date | `depends_on: eval:doc.is_event`, `mandatory_depends_on: eval:doc.is_event` |
| `event_location` | Data | Location | `depends_on: eval:doc.is_event`, optional |

`event_date` and `event_location` are hidden and ignored by the desk until **Is Event**
is ticked; `event_date` then becomes mandatory.

### 2. API serializers

The `blog` app builds its list payload in
`blog.blog.doctype.blog_post.blog_post.get_blog_list()`, which selects columns explicitly,
so the new fields were missing from the response. This app wraps that function
(`custom_blog/blog_api.py`) so `is_event`, `event_date` and `event_location` are added to
**every** blog list payload — `/blog`, category pages, author pages and the website
templates that go through `get_list_context`.

The blog detail page already returns the full document
(`frappe/website/page_renderers/document_page.py` does `context.update(doc.as_dict())`),
so it carries the event fields automatically once installed. A whitelisted detail
serializer is provided as well.

#### Endpoints

```
GET /api/method/custom_blog.api.get_blog_list
    ?txt=&filters={"blog_category":"news"}&limit_start=0&limit_page_length=20

GET /api/method/custom_blog.api.get_blog_post
    ?name=<blog post name>
```

Both accept guests. `get_blog_list` only returns published posts; `get_blog_post` returns
`404` for unpublished posts unless the user has a Blogger / Website Manager / System
Manager / Administrator role.

Response excerpt:

```json
{
  "name": "launch-party",
  "title": "Launch Party",
  "route": "news/launch-party",
  "blogger": "Jane Doe",
  "published_on": "2026-10-04",
  "cover_image": "/files/lunch.png",
  "category": { "name": "News", "route": "news", "title": "News" },
  "author": { "name": "jane", "full_name": "Jane Doe", "avatar": "/files/jane.png" },
  "is_event": 1,
  "event_date": "2026-11-20",
  "event_location": "Bengaluru"
}
```

## Install

Copy the app into your bench, then:

```bash
bench get-app file:///home/<you>/custom_blog      # or copy the folder to apps/
bench --site <site> install-app custom_blog
bench --site <site> migrate
bench --site <site> clear-cache
```

`after_install` creates the fields and runs `updatedb` for them; the patch in
`patches.txt` (`custom_blog.patches.v0_1.add_event_fields`) makes the same setup run
idempotently on `bench migrate`. Uninstalling removes the Custom Fields again.

`custom_blog` declares `required_apps = ["blog"]`, so `blog` must be installed first.

## Frontend

```js
// list
frappe.call({ method: "custom_blog.api.get_blog_list", args: { limit_page_length: 20 } })
	.then(({ message }) => message.filter((p) => p.is_event));

// detail
frappe.call({ method: "custom_blog.api.get_blog_post", args: { name: "launch-party" } })
	.then(({ message }) => {
		frappe.msgprint(`${message.title} — ${message.event_date} @ ${message.event_location}`);
	});
```

## Layout

```
custom_blog/
├── __init__.py
├── api.py                  # whitelisted REST endpoints
├── blog_api.py             # get_blog_list patch + serializers
├── custom_fields.py        # Blog Post event fields definition
├── hooks.py
├── install.py              # after_install / before_uninstall
├── modules.txt
├── patches.txt
├── custom_blog/            # "Custom Blog" module (no doctypes)
└── patches/v0_1/add_event_fields.py
```

## License

MIT