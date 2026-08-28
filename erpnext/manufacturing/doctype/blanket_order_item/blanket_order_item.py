# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


def get_submitted_po_qty(blanket_order_item):
	"""
	Total quantity of *submitted* Purchase Order lines allocated to one Blanket Order line.

	Submitted-only is deliberate and was confirmed by Brian on 2026-08-28: a draft
	Purchase Order does not reserve quantity against a blanket contract.

	This is the single source of truth for 'ordered_qty'.  Two hand-written copies of
	this query used to exist -- here and in PurchaseOrder.on_update() -- and they
	disagreed about drafts, so the remaining contract quantity depended on which one
	wrote last.
	"""
	sql_query = """
		SELECT IFNULL(SUM(PurchaseLine.qty),0) 		AS qty
		FROM `tabPurchase Order Item`	AS PurchaseLine
		INNER JOIN `tabPurchase Order`		AS PurchaseOrder
		ON PurchaseOrder.name = PurchaseLine.parent
		WHERE PurchaseLine.blanket_order_item = %(blanket_line_key)s
		AND PurchaseOrder.docstatus = 1
	"""
	po_quantities = frappe.db.sql(sql_query, values={'blanket_line_key': blanket_order_item})
	return po_quantities[0][0] if po_quantities else 0


# SF_MOD_0001 : Blanket Order Items
class BlanketOrderItem(Document):
	def update_ordered_qty(self):
		"""
		Update line 'ordered_qty' by aggregating the Submitted quantity of related PO lines.
		"""
		# TODO: Long Term: Rather than storing in SQL, can we not cache this and use a 'display method'?
		blanket_order_type = frappe.get_doc('Blanket Order', self.parent).blanket_order_type
		if blanket_order_type == "Selling":
			return

		ordered_qty = get_submitted_po_qty(self.name)
		# Cannot use the ORM, because we're not allowed to update Cancelled documents.
		frappe.db.set_value('Blanket Order Item', self.name, 'ordered_qty', ordered_qty)
		frappe.db.commit()
		return ordered_qty


	def set_new_weight_per_uom(self, new_value):
		"""
		Called by Frontend JS code to change the conversion factor of Weight (e.g. Lbs) to UOM (e.g. Drum)
		Normally the value is determined by the Item table, but SF occassionally must alter it.

		"""
		self.weight_per_unit = new_value
		self.total_weight = self.qty * self.weight_per_unit
		self.qty_in_weight_uom = self.qty * self.weight_per_unit
		self.rate_per_weight_uom = self.rate / self.weight_per_unit
		self.db_update()
		# frappe.db.set_value('Blanket Order Item', self.name, 'weight_per_unit', new_value)

		frappe.db.commit()
