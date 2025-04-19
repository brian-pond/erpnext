from frappe import _

# DH: Altering some of the Connection links.

def get_data():
	return {
		"fieldname": "customer",
		"non_standard_fieldnames": {
			"Payment Entry": "party",
			"Quotation": "party_name",
			"Opportunity": "party_name",
			"Bank Account": "party",
			"Subscription": "party",
			"Item Favorites": "customer_key"
		},
		"dynamic_links": {"party_name": ["Customer", "quotation_to"]},
		"transactions": [
			# {"label": _("Pre Sales"), "items": ["Opportunity", "Quotation"]},
			{"label": _("Website"), "items": ["Auth User", "Item Favorites"]},
			{"label": _("Orders"), "items": ["Daily Order", "Delivery Note", "Sales Invoice"]},
			{"label": _("Payments"), "items": ["Payment Entry", "Bank Account"]},
			#{
			#	"label": _("Support"),
			#	"items": ["Issue", "Maintenance Visit", "Installation Note", "Warranty Claim"],
			#},
			#{"label": _("Projects"), "items": ["Project"]},
			{"label": _("Pricing"), "items": ["Pricing Rule"]},
			{"label": _("Customer Subscriptions"), "items": ["Customer Subscription"]},
		],
	}
