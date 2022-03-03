# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


# Spectrum Fruits
# Custom Fields include the following:
#   * qty_in_weight_uom
#   * rate_per_weight_uom


from __future__ import unicode_literals
# import frappe

from frappe.model.document import Document
from erpnext.controllers.print_settings import print_settings_for_item_table

class DeliveryNoteItem(Document):
	def __setup__(self):
		print_settings_for_item_table(self)
