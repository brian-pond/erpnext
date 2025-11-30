# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class UOMConversionFactor(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		category: DF.Link
		from_uom: DF.Link
		to_uom: DF.Link
		value: DF.Float
	# end: auto-generated types


def on_doctype_update():
	# Datahenge: Incredibly important to prevent duplicate conversion factors for the same From and To pairs.
	frappe.db.add_unique("UOM Conversion Factor", ["from_uom", "to_uom"], constraint_name="uom_conversion_factor_from_to")
