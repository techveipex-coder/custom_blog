# Custom Blog

Extension app for the `blog` app (Frappe/ERPNext **v16**). It adds **event** support to
`Blog Post` — event fields, guest registration and a signup count — without editing the
`blog` app itself.

## What it does

### 1. Blog Post fields

Four fields are added to `Blog Post` as Custom Fields (`is_event` section, collapsible):

| Field | Type | Label | Rules |
| --- | --- | --- | --- |
| `is_event` | Check | Is Event | default `0` |
| `event_date` | Date | Event Date | `depends_on: eval:doc.is_event`, `mandatory_depends_on: eval:doc.is_event` |
| `event_location` | Data | Location | `depends_on: eval:doc.is_event`, optional |
| `is_owned_by_us` | Check | Hosted by VEIPEX | default `0`, `depends_on: eval:doc.is_event` |

`event_date`, `event_location` and `is_owned_by_us` are hidden and ignored by the desk
until **Is Event** is ticked; `event_date` then becomes mandatory.

### 2. API serializers

The `blog` app builds its list payload in
`blog.blog.doctype.blog_post.blog_post.get_blog_list()`, which selects columns explicitly,
so the new fields were missing from the response. This app wraps that function
(`custom_blog/blog_api.py`) so the event fields are added to **every** blog list payload —
`/blog`, category pages, author pages and the website templates that go through
`get_list_context`.

The blog detail page already returns the full document
(`frappe/website/page_renderers/document_page.py` does `context.update(doc.as_dict())`),
so it carries the event fields automatically once installed. A whitelisted detail
serializer is provided as well.

#### `can_register`

Both payloads (`get_blog_list` and `get_blog_post`) also carry a derived, **never stored**
flag so the frontend does not have to evaluate dates:

```
can_register = is_event AND is_owned_by_us AND event_date >= today()
```

It is computed per response (`custom_blog.blog_api.can_register`) instead of stored
because it depends on the current date — a stored value would go stale as soon as the
event date passes. A post that is not an event, is not hosted by VEIPEX, has no date, or
whose date is in the past always yields `0`.

### 3. `Blog Event Signup` and registration

Registrations are stored in the `Blog Event Signup` DocType shipped by this app:

| Field | Type | Rules |
| --- | --- | --- |
| `blog_post` | Link → Blog Post | mandatory |
| `full_name` | Data | mandatory |
| `email` | Data | mandatory, `options: Email` (validated) |
| `phone` | Data | mandatory, `options: Phone` (validated) |
| `registered_on` | Datetime | default `Now`, read-only |

`register_for_event` re-runs the `can_register` rules server-side via
`blog_api.registration_blocker()` — the flag the frontend sends is only a hint for
rendering the button, never the authority to accept a signup. Each failure mode has its
own message so the UI can show something meaningful:

| Situation | Message |
| --- | --- |
| `is_event` / `is_owned_by_us` not set | This isn't an event we're hosting |
| no `event_date` | This event has no date set |
| `event_date` in the past | Registration for this event has closed |
| blank name / email / phone | Please fill in \<missing labels\> |
| unreadable or unpublished post | 404 / Not permitted to read this Blog Post |

Duplicate signups (same email, same post) are **not** an error: the response is
`success: true` with `already_registered: true` and a friendly message, since the
guest's intent is already satisfied.

No role holds insert permission on `Blog Event Signup`; rows are only created by the
endpoint (which inserts with `ignore_permissions=True` after validating everything
itself), so guests cannot post signups through the generic DocType API.

#### Endpoints

```
GET  /api/method/custom_blog.api.get_blog_list
      ?txt=&filters={"blog_category":"news"}&limit_start=0&limit_page_length=20

GET  /api/method/custom_blog.api.get_blog_post
      ?name=<blog post name>

POST /api/method/custom_blog.api.register_for_event
      blog_post=<name>&full_name=Asha Rao&email=asha@example.com&phone=+919845000001

GET  /api/method/custom_blog.api.get_event_signup_count
      ?blog_post=<blog post name>
```

All of them accept guests. `get_blog_list` only returns published posts;
`get_blog_post` and `register_for_event` return `404` for unpublished posts unless the
user has a Blogger / Website Manager / System Manager / Administrator role.
`register_for_event` answers with `{ success: true, message, blog_post, ... }`.

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
  "event_location": "Bengaluru",
  "is_owned_by_us": 1,
  "can_register": 1
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

`after_install` creates the fields and runs `updatedb` for them; the patches in
`patches.txt` (`custom_blog.patches.v0_1.add_event_fields` and
`custom_blog.patches.v0_2.add_event_ownership_and_signups`) make the same setup run
idempotently on `bench migrate`. A patch is recorded in the site's Patch Log and never
re-runs, so **newly added fields always ship with a new patch** — otherwise already
migrated sites would never get them. Uninstalling removes the Custom Fields again.

`custom_blog` declares `required_apps = ["blog"]`, so `blog` must be installed first.

### Fields not showing on the Blog Post form

1. Run `bench --site <site> migrate` (picks up new Custom Fields and creates the
   `Blog Event Signup` table), then `bench --site <site> clear-cache` and reload.
2. The event fields live in a **collapsible** "Event Details" section after *Featured* —
   expand it.
3. `event_date`, `event_location` and `is_owned_by_us` are only shown once **Is Event**
   is ticked (`depends_on: eval:doc.is_event`). `is_event` is always visible.

## Frontend

```js
// list -- `can_register` is precomputed, no date logic needed in the frontend
frappe.call({ method: "custom_blog.api.get_blog_list", args: { limit_page_length: 20 } })
	.then(({ message }) => {
		message.forEach((post) => {
			if (post.can_register) frappe.msgprint(`Register for ${post.title} @ ${post.event_location}`);
		});
	});

// detail
frappe.call({ method: "custom_blog.api.get_blog_post", args: { name: "launch-party" } })
	.then(({ message }) => {
		frappe.msgprint(`${message.title} — ${message.event_date} @ ${message.event_location}`);
	});

// register (only render the form when `can_register`, the server checks again)
frappe.call({
	method: "custom_blog.api.register_for_event",
	args: { blog_post: "launch-party", full_name: "Asha Rao", email: "asha@example.com", phone: "+91 98450 00001" }
}).then(({ message }) => frappe.msgprint(message)); // "You're registered for Launch Party. See you there!"

// "X people are attending"
frappe.call({ method: "custom_blog.api.get_event_signup_count", args: { blog_post: "launch-party" } })
	.then(({ message }) => frappe.msgprint(`${message} people are attending`));
```

## Layout

```
custom_blog/
├── __init__.py
├── api.py                  # whitelisted REST endpoints + registration
├── blog_api.py             # get_blog_list patch + serializers + can_register
├── custom_fields.py        # Blog Post event fields definition
├── hooks.py
├── install.py              # after_install / before_uninstall
├── modules.txt
├── patches.txt
├── test_blog_api.py        # event fields + can_register tests
├── custom_blog/            # "Custom Blog" module
│   └── doctype/
│       └── blog_event_signup/
│           ├── blog_event_signup.json
│           ├── blog_event_signup.py
│           └── test_blog_event_signup.py
└── patches/v0_1/add_event_fields.py
```

Run them with `bench --site <site> run-tests --app custom_blog`.

## License

MIT