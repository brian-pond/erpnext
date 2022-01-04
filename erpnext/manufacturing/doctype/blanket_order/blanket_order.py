# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from datetime import date

import frappe
from frappe import _  # pylint: disable=unused-import
from frappe.contacts.doctype.address.address import get_address_display
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, today as today_str

from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.get_item_details import get_conversion_factor

class BlanketOrder(Document):

	def validate(self):
		# self.validate_dates()

		# TODO: Check this out Brian
		self.set_supplier_address()
		self.validate_required_by_dates()

	def on_update(self):

		# Recalculate the Grand Total after each insert/update.
		self.amount_grand_total = 0.0
		for order_line in self.items:
			order_line.line_amount = order_line.qty * order_line.rate
			self.amount_grand_total += order_line.line_amount if order_line.line_amount else 0.0

	# Spectrum Fruits: No reason to include a -range- of Dates for blanket orders.
	# def validate_dates(self):
	#	if getdate(self.from_date) > getdate(self.to_date):
	#		frappe.throw(_("From date cannot be greater than To date"))

	def update_ordered_qty(self):
		"""
		Spectrum Fruits: Loop through blanket lines, and update their 'ordered_qty' from POs.
		"""
		for line in self.items:
			line.update_ordered_qty()

	def set_supplier_address(self):
		address_dict = {
			'party_billing_address': 'party_billing_address_display',
		}
		for address_field, address_display_field in address_dict.items():
			if self.get(address_field):
				self.set(address_display_field, get_address_display(self.get(address_field)))

	def validate_required_by_dates(self):
		if not self.get("items"):
			return

		if any(d.reqd_by_date for d in self.get("items")):
			# Set header 'From Date' = earliest 'Required By Date' from lines.
			self.from_date = min(d.reqd_by_date for d in self.get("items")
							if d.reqd_by_date is not None)

		if self.from_date:
			for order_line in self.get('items'):
				if not order_line.reqd_by_date:
					order_line.reqd_by_date = self.from_date

		# There's no reason for validating the 'From Date'; it's just a default
				#if (d.reqd_by_date and self.from_date and
				#	getdate(d.reqd_by_date) < getdate(self.from_date)):
				#	frappe.throw(_("Row #{0}: 'Reqd by Date' cannot preceed 'From Date'").format(d.idx))
		# else:
		# 	frappe.throw(_("Please enter 'From Date'"))

	@frappe.whitelist()
	def revert_to_draft(self):
		"""
		Update the Blanket Order so that it's back into a Draft status.
		"""
		frappe.db.set_value(self.doctype, self.name, "docstatus", 0)
		# Order Lines:
		frappe.db.sql("""UPDATE `tabBlanket Order Item` SET docstatus = 0 WHERE parent = %s""", self.name)



@frappe.whitelist()
def make_sales_order(source_name):
	def update_item(source, target, source_parent):
		target_qty = source.get("qty") - source.get("ordered_qty")
		target.qty = target_qty if not flt(target_qty) < 0 else 0
		item = get_item_defaults(target.item_code, source_parent.company)
		if item:
			target.item_name = item.get("item_name")
			target.description = item.get("description")
			target.uom = item.get("stock_uom")

	target_doc = get_mapped_doc("Blanket Order", source_name, {
		"Blanket Order": {
			"doctype": "Sales Order"
		},
		"Blanket Order Item": {
			"doctype": "Sales Order Item",
			"field_map": {
				"rate": "blanket_order_rate",
				"parent": "blanket_order"
			},
			"postprocess": update_item
		}
	})
	return target_doc

@frappe.whitelist()
def make_purchase_order(blanket_order_id):
	"""
	Create a new Purchase Order based on Blanket Order.
	"""

	def update_lines(blanket_line, target_line, blanket_order):
		# How much Blanket Qty is not-yet allocated to POs?
		qty_remaining = blanket_line.get("qty") - blanket_line.get("ordered_qty")
		target_line.qty = qty_remaining if not flt(qty_remaining) < 0 else 0

		# PO line's requirement date cannot preceed today's date.
		if target_line.schedule_date < date.today():
			target_line.schedule_date = today_str()

		# Fetch default values from Item table.
		item_defaults = get_item_defaults(target_line.item_code, blanket_order.company)
		# Update PO lines accordingly
		if item_defaults:
			target_line.item_name = item_defaults.get("item_name")
			if not blanket_line.description:  # Brian: If Blanket Order line missing description, fetch from Item Master.
				target_line.description = item_defaults.get("description")
			target_line.stock_uom = item_defaults.get("stock_uom")

	# SF_MOD_0001: Copy 'required by date'
	# method, source_name, selected_children=None, args=None):
	target_doc = get_mapped_doc("Blanket Order", blanket_order_id, {
		"Blanket Order": {
			"doctype": "Purchase Order",
			"field_map": {
				"blanket_order": "name",
				"party_billing_address": "supplier_address",
				"warehouse_default": "set_warehouse"
			}
		},
		# Blanket Field : PO Field
		"Blanket Order Item": {
			"doctype": "Purchase Order Item",
			"field_map": {
				"rate": "blanket_order_rate",
				"parent": "blanket_order",
				"name": "blanket_order_item",
				"description": "description",
				"reqd_by_date": "schedule_date",
				"uom_weight": "weight_uom",
				"uom_buying": "uom",
				"total_weight": "total_weight",
				"warehouse": "warehouse"
			},
			"postprocess": update_lines
		}
	})
	target_doc.schedule_date = today_str()
	target_doc.naming_series = 'PO-'
	# If Buying Settings require that a PO link to 1 (and only 1) Blanket Order?
	# Then indicate that blanket order on the PO's header.
	if bool(frappe.db.get_single_value('Buying Settings', 'single_blanket_per_po')) is True:
		target_doc.blanket_order = blanket_order_id
	return target_doc


@frappe.whitelist()
def get_item_details(item_code, uom=None):
	"""
	When selecting a new Item on a blanket order line, there are many fields
	required from Item table.
	"""
	details = frappe.db.get_value('Item', item_code,
	   ['stock_uom', 'name', 'description', 'purchase_uom', 'weight_uom', 'weight_per_unit'], as_dict=1)
	details.uom = uom or details.stock_uom
	if uom:
		details.update(get_conversion_factor(item_code, uom))
	return details
