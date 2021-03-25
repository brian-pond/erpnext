# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults
from frappe import msgprint, _
from frappe.model.naming import set_name_by_naming_series
from frappe.contacts.address_and_contact import load_address_and_contact, delete_contact_and_address
from erpnext.utilities.transaction_base import TransactionBase
from erpnext.accounts.party import validate_party_accounts, get_dashboard_info, get_timeline_data # keep this


class Supplier(TransactionBase):
	def get_feed(self):
		return self.supplier_name

	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)
		self.load_dashboard_info()

	def before_save(self):
		if not self.on_hold:
			self.hold_type = ''
			self.release_date = ''
		elif self.on_hold and not self.hold_type:
			self.hold_type = 'All'

	def load_dashboard_info(self):
		info = get_dashboard_info(self.doctype, self.name)
		self.set_onload('dashboard_info', info)

	def autoname(self):
		supp_master_name = frappe.defaults.get_global_default('supp_master_name')
		if supp_master_name == 'Supplier Name':
			self.name = self.supplier_name
		else:
			set_name_by_naming_series(self)

	def on_update(self):
		if not self.naming_series:
			self.naming_series = ''

	def validate(self):
		# validation for Naming Series mandatory field...
		if frappe.defaults.get_global_default('supp_master_name') == 'Naming Series':
			if not self.naming_series:
				msgprint(_("Series is mandatory"), raise_exception=1)

		validate_party_accounts(self)

	def on_trash(self):
		""" When deleting supplier, delete related Contacts and Addresses. """
		delete_contact_and_address('Supplier', self.name)

	def after_rename(self, olddn, newdn, merge=False):
		if frappe.defaults.get_global_default('supp_master_name') == 'Supplier Name':
			frappe.db.set(self, "supplier_name", newdn)

	def get_remit_to_address(self, first_only=False):
		""" Spectrum Fruits: Get a supplier's 'Remit To' address. """

		# Using this function to find the appropriate address for new Bank Checks.
		filters = [
			["Dynamic Link", "link_doctype", "=", "Supplier"],
			["Dynamic Link", "link_name", "=", self.name],
			["Dynamic Link", "parenttype", "=", "Address"],
			["Address", "address_type", "=", "Remit To"],
		]

		address_list = frappe.get_all("Address", filters=filters, fields=["name"])
		if not address_list or len(address_list) == 0:
			frappe.error(_(f"Unable to find default 'Remit To' address for Supplier {self.name}."))
		if (len(address_list) > 1) and not first_only:
			frappe.error(_(f"Found multiple 'Remit To' address records for Supplier {self.name}."))
		ret = frappe.get_doc("Address", address_list[0]['name'])
		return ret
