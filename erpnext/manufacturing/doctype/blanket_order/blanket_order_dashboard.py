from __future__ import unicode_literals
from frappe import _

# Brian: The 'items' are in fact links on the Dashboard.
# The 'fieldname' is which column in those tables links to this DocType's name.
def get_data():
	return {
		'fieldname': 'blanket_order',
		'transactions': [
			{
				'items': ['Purchase Order', 'Sales Order']
			}
		]
	}
