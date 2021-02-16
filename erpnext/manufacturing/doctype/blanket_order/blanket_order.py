# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_address_display
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, getdate

from erpnext.stock.doctype.item.item import get_item_defaults


class BlanketOrder(Document):
	def __init__(self, *args, **kwargs):
		super(BlanketOrder, self).__init__(*args, **kwargs)

	def validate(self):
		self.validate_dates()
		self.set_supplier_address()

	def validate_dates(self):
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From date cannot be greater than To date")) 

	def update_ordered_qty(self):
		# SF_MOD_0001: Update each blanket order line individually.
		for d in self.items:
			d.update_ordered_qty()

	def set_supplier_address(self):
		address_dict = {
			'party_billing_address': 'party_billing_address_display',
		}
		for address_field, address_display_field in address_dict.items():
			if self.get(address_field):
				self.set(address_display_field, get_address_display(self.get(address_field)))

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
def make_purchase_order(source_name):
	""" Create a new Purchase Order based on Blanket Order. """

	def update_lines(blanket_line, target_line, blanket_order):
		qty_remaining = blanket_line.get("qty") - blanket_line.get("ordered_qty")
		target_line.qty = qty_remaining if not flt(qty_remaining) < 0 else 0
		
		# SF:  Purchase Lines point at Blanket Lines.
		target_line.schedule_date = blanket_line.reqd_by_date
		target_line.blanket_order_item = blanket_line.name

		# Fetch default values from Item table.
		item_defaults = get_item_defaults(target_line.item_code, blanket_order.company)
		if item_defaults:
			target_line.item_name = item_defaults.get("item_name")
			target_line.description = item_defaults.get("description")
			target_line.uom = item_defaults.get("stock_uom")
			target_line.warehouse = item_defaults.get("default_warehouse")

	# SF_MOD_0001: Copy 'required by date'
	# method, source_name, selected_children=None, args=None):
	target_doc = get_mapped_doc("Blanket Order", source_name, {
		"Blanket Order": {
			"doctype": "Purchase Order",
			"field_map": {
				"blanket_order": "name"
			}
		},
		"Blanket Order Item": {
			"doctype": "Purchase Order Item",
			"field_map": {
				"rate": "blanket_order_rate",
				"parent": "blanket_order",
				"schedule_date": "reqd_by_date",
				"blanket_order_item": "name"
			},
			"postprocess": update_lines
		}
	})

	blanket_order = frappe.get_doc('Blanket Order', source_name)
	earliest_reqd_by_date = min([d.reqd_by_date for d in blanket_order.get("items")])

	target_doc.schedule_date = earliest_reqd_by_date
	target_doc.naming_series = 'PO-'
	return target_doc
