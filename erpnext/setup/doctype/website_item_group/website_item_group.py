# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

# For license information, please see license.txt


from frappe.model.document import Document


class WebsiteItemGroup(Document):
	pass
<<<<<<< HEAD

def on_doctype_update():
	# Farm To People:  Do not allow the same Item Group to be assigned twice (bug in standard code)
	frappe.db.add_index("Website Item Group", ["parent", "parenttype", "item_group"])
	frappe.db.add_unique("Website Item Group", ["parent", "parenttype", "item_group"])
=======
>>>>>>> temp1
