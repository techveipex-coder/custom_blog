"""Custom Fields added to `Blog Post` (blog app, v16).

The fields are added as Custom Field records on install, so the upstream
`blog` app stays untouched and upgradeable.

Fields:
	is_event       Check, default 0 -- "Is Event"
	event_date     Date, mandatory + visible only when is_event = 1
	event_location Data, visible only when is_event = 1, label "Location"
"""

EVENT_FIELDS = [
	{
		"fieldname": "section_break_event",
		"fieldtype": "Section Break",
		"label": "Event Details",
		"insert_after": "featured",
		"collapsible": 1,
	},
	{
		"fieldname": "is_event",
		"fieldtype": "Check",
		"label": "Is Event",
		"default": "0",
		"insert_after": "section_break_event",
	},
	{
		"fieldname": "event_date",
		"fieldtype": "Date",
		"label": "Event Date",
		"insert_after": "is_event",
		"depends_on": "eval:doc.is_event",
		"mandatory_depends_on": "eval:doc.is_event",
	},
	{
		"fieldname": "event_location",
		"fieldtype": "Data",
		"label": "Location",
		"insert_after": "event_date",
		"depends_on": "eval:doc.is_event",
	},
]

EVENT_FIELDNAMES = ("is_event", "event_date", "event_location")

#: values used when a field is not installed on the DocType yet
EVENT_FIELD_DEFAULTS = {"is_event": 0, "event_date": None, "event_location": None}

CUSTOM_FIELDS = {"Blog Post": EVENT_FIELDS}