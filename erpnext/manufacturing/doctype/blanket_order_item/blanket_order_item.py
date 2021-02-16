# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

# SF_MOD_0001 : Blanket Orders
class BlanketOrderItem(Document):
	def update_ordered_qty(self):
		""" Update line 'ordered_qty' based on actual PO/SO value.
			TODO: Rather than storing in SQL, can we not cache this and use a 'display method'?
		"""
		# Sum quantity per Blanket Order line name.
		blanket_order_type = frappe.get_doc('Blanket Order', self.parent).blanket_order_type
		ref_doctype = "Sales Order" if blanket_order_type == "Selling" else "Purchase Order"
		item_ordered_qty = frappe.db.sql("""
			SELECT SUM(trans_item.stock_qty) as qty
			FROM `tab{0} Item` trans_item

			INNER JOIN `tab{0}` trans
			ON trans.name = trans_item.parent
			AND trans.docstatus=1
			AND trans.status not in ('Closed', 'Stopped')

			WHERE trans_item.blanket_order_item = '{1}'
		""".format(ref_doctype, self.name))

		self.ordered_qty = item_ordered_qty[0][0]
		self.save()
