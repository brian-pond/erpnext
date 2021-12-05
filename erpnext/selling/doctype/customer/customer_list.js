frappe.listview_settings['Customer'] = {

	/*
	Datahenge: This is a workaround, but a useful one.
	By default, the List Page is defaulting the Customer Group based
	on Selling Settings.  So far, I've been unable to debug the code 
	in the core, and resolve why/how this happens.

	I "think" it's using 'bootinfo.sysdefaults.customer_group' or sys_defaults.
	But it's pretty obscure.

	In the meantime, this resolves the Filter issue, but allows the Default Value
	to continue.
	*/

	onload: function(listview) {
		if (!frappe.route_options) { 
			frappe.route_options = {
				"customer_group": ["=", ""],
				"territory": ["=", ""],
			};
		}
	},

	add_fields: ["customer_name", "territory", "customer_group", "customer_type", "image"],
};
