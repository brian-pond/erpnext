// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// In development, Bundling is not necessary for changes to take effect.

frappe.ui.form.on('Blanket Order', {
	onload: function(frm, cdt, cdn) {
		// Filter 'party_billing_address' based on either Customer or Supplier
		frm.set_query("party_billing_address", get_address_query);
		frm.trigger('set_tc_name_filter');
		frm.trigger('blanket_order_type');

		render_grand_total(frm, cdt, cdn)
		// var current_doc = locals[cdt][cdn];	
		// console.log(current_doc.supplier)
	},

	supplier: (frm, cdt, cdn) => {
		// When Supplier is edited, clear the address fields.
		custom_clear_address(frm);
	},

	customer: (frm, cdt, cdn) => {
		// When Customer is edited, clear the address fields.
		custom_clear_address(frm);
	},

	party_billing_address: (frm, cdt, cdn) => {
		// When address is updated, automatically change the value of "party_billing_address_display"
		// Signature:  add_fetch(link_fieldname, source_fieldname, target_fieldname)
		// This only works because of the Link relationship to Customer.
	
	},

	setup: function(frm) {
		// Used here to populate read-only fields Customer Name and Supplier Name
		frm.add_fetch("customer", "customer_name", "customer_name");
		frm.add_fetch("supplier", "supplier_name", "supplier_name");
	},

	refresh: function(frm) {
		erpnext.hide_company();
		if (frm.doc.customer && frm.doc.docstatus === 1) {
			frm.add_custom_button(__('View Orders'), function() {
				frappe.set_route('List', 'Sales Order', {blanket_order: frm.doc.name});
			});
			frm.add_custom_button(__("Create Sales Order"), function(){
				frappe.model.open_mapped_doc({
					method: "erpnext.manufacturing.doctype.blanket_order.blanket_order.make_sales_order",
					frm: frm
				});
			}).addClass("btn-primary");
		}

		if (frm.doc.supplier && frm.doc.docstatus === 1) {
			frm.add_custom_button(__('View Orders'), function() {
				frappe.set_route('List', 'Purchase Order', {blanket_order: frm.doc.name});
			});
			frm.add_custom_button(__("Create Purchase Order"), function(){
				frappe.model.open_mapped_doc({
					method: "erpnext.manufacturing.doctype.blanket_order.blanket_order.make_purchase_order",
					frm: frm
				});
			}).addClass("btn-primary");
		}
	},

	onload_post_render: function(frm) {
		frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},

	tc_name: function (frm) {
		erpnext.utils.get_terms(frm.doc.tc_name, frm.doc, function (r) {
			if (!r.exc) {
				frm.set_value("terms", r.message);
			}
		});
	},

	set_tc_name_filter: function(frm) {
		if (frm.doc.blanket_order_type === 'Selling') {
			frm.set_df_property("customer","reqd", 1);
			frm.set_df_property("supplier","reqd", 0);
			frm.set_value("supplier", "");

			frm.set_query("tc_name", function() {
				return { filters: { selling: 1 } };
			});
		}
		if (frm.doc.blanket_order_type === 'Purchasing') {
			frm.set_df_property("supplier","reqd", 1);
			frm.set_df_property("customer","reqd", 0);
			frm.set_value("customer", "");

			frm.set_query("tc_name", function() {
				return { filters: { buying: 1 } };
			});
		}
	},

	blanket_order_type: function (frm) {
		frm.trigger('set_tc_name_filter');
	},

	/* eslint-enable */
});


function get_address_query (doc) {
	if (doc.supplier) {
		// Blanket Purchase Order					
		return {
			query: 'frappe.contacts.doctype.address.address.address_query',
			filters: { link_doctype: 'Supplier', link_name: doc.supplier }
		};
	}
	if (doc.customer) {
		// Blanket Sales Order
		return {
			query: 'frappe.contacts.doctype.address.address.address_query',
			filters: { link_doctype: 'Customer', link_name: doc.customer }
		};
	}			
}	


function custom_clear_address (frm) {
	if (frm.doc.party_billing_address){
		frm.set_value("party_billing_address", "");
		frm.set_value("party_billing_address_display", "");
	}
	frm.set_query("party_billing_address", get_address_query);
}


function render_grand_total (frm) {

	frm.doc.blanket_order.tmp_hello = "Hello";

	/*
	const parent = $('<div class="range-selector')


	const  grand_total_field = frappe.ui.form.make_control({
		df: {
			label: 'Grand Total',
			fieldname: 'blanket_grand_total',
			fieldtype: 'Date'
		},
		parent: frm.field_html.wrapper,
		render_input: true
	})
	*/
}