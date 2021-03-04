# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

# SF_MOD_0001 : Blanket Order Items
class BlanketOrderItem(Document):
	def update_ordered_qty(self):
		""" Update line 'ordered_qty' based on actual PO/SO value.
			TODO: Rather than storing in SQL, can we not cache this and use a 'display method'?
		"""
		# Sum quantity per Blanket Order line name.
		blanket_order_type = frappe.get_doc('Blanket Order', self.parent).blanket_order_type
		if blanket_order_type == "Selling":
			return

		sql_query = """
			SELECT IFNULL(SUM(purchase_line.qty),0) as qty
			FROM `tabPurchase Order Item` AS purchase_line
			WHERE purchase_line.blanket_order_item = '{0}'
			AND purchase_line.docstatus = 1
			
		""".format(self.name)

		# AND purchase_line.status not in ('Closed', 'Stopped')
		item_ordered_qty = frappe.db.sql(sql_query)
		# Cannot use the ORM, because we're not allowed to update Cancelled documents.
		frappe.db.set_value('Blanket Order Item', self.name, 'ordered_qty',  item_ordered_qty[0][0])
