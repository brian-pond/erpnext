frappe.pages['page-bank-reconciliation'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'DNU - Bank Reconciliation',
		single_column: true
	});
}