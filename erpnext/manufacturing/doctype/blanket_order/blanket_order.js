// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// Copyright (c) 2022, Datahenge LLC
// For license information, please see license.txt

frappe.provide("erpnext.manufacturing");

frappe.ui.form.on('Blanket Order', {

	onload: function(frm, cdt, cdn) {

		cur_frm.dashboard.frm.fields[0].df.hidden=1  // Hide the Dashboard

		if (!frm.doc.from_date){
			frm.set_value('from_date', frappe.datetime.get_today())
		}
		if (!frm.doc.document_date){
			frm.set_value('document_date', frappe.datetime.get_today())
		}

		// Fill-in any missing values.
		default_reqd_by_dates(frm);
		default_line_warehouse(frm);

		// Filter 'party_billing_address' based on either Customer or Supplier
		frm.set_query("party_billing_address", get_address_query);

		frm.trigger('set_tc_name_filter');
		frm.trigger('blanket_order_type');

		// render_grand_total(frm, cdt, cdn)
	},

	validate: function(frm) {
		default_reqd_by_dates(frm);
		default_line_warehouse(frm);
	},

	items_on_form_rendered: function(frm) {
		// Datahenge: This function is called when the child grid is opened in full-screen.
	},

	setup: function(frm) {
		// Used here to populate read-only fields Customer Name and Supplier Name
		frm.add_fetch("customer", "customer_name", "customer_name");
		frm.add_fetch("supplier", "supplier_name", "supplier_name");
	},

	onload_post_render: function(frm) {
		frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},

	toggle_conversion_factor: function(frm, item) {
		// toggle read only property for conversion factor field if the uom and stock uom are same
		if(frm.get_field('items').grid.fields_map.conversion_factor) {
			frm.fields_dict.items.grid.toggle_enable("conversion_factor",
				((item.uom != item.stock_uom) && !frappe.meta.get_docfield(cur_frm.fields_dict.items.grid.doctype, "conversion_factor").read_only)? true: false);
		}
	},

	conversion_factor: function(doc, cdt, cdn, dont_fetch_price_list_rate) {
		if(frappe.meta.get_docfield(cdt, "stock_qty", cdn)) {
			var item = frappe.get_doc(cdt, cdn);
			frappe.model.round_floats_in(item, ["qty", "conversion_factor"]);
			item.stock_qty = flt(item.qty * item.conversion_factor, precision("stock_qty", item));
			refresh_field("stock_qty", item.name, item.parentfield);
			this.toggle_conversion_factor(item);

			if(doc.doctype != "Material Request") {
				item.total_weight = flt(item.stock_qty * item.weight_per_unit);
				refresh_field("total_weight", item.name, item.parentfield);
				this.calculate_net_weight();
			}

			if (!dont_fetch_price_list_rate &&
				frappe.meta.has_field(doc.doctype, "price_list_currency")) {
				this.apply_price_list(item, true);
			}
		}
	},

	/* ----------------
	    DocFields
	   ----------------*/
	supplier: (frm) => {
		// When Supplier is edited, clear the address fields.
		custom_clear_address(frm);
	},

	customer: (frm) => {
		// When Customer is edited, clear the address fields.
		custom_clear_address(frm);
	},

	party_billing_address: (frm, cdt, cdn) => {
		// When address is updated, automatically change the value of "party_billing_address_display"
		// Signature:  add_fetch(link_fieldname, source_fieldname, target_fieldname)
		// Works because of the Link relationship to Customer.
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
	_revert_to_draft(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'revert_to_draft',
			callback: function() {
				frm.reload_doc() && frm.refresh();
			}
		});
	},

});


/* 
	Datahenge: Still not quite sure why I'm wrapping/extending form.Controller?
	But it's necessary to call get_item_details() successfully
*/
	
erpnext.manufacturing.BlanketOrder = frappe.ui.form.Controller.extend({

	refresh: function() {
		var me = this;  // because the meaning of 'this' changes in contexts
		erpnext.hide_company();

		this.frm.add_custom_button(__('Recalculate Quantity on PO'), function() {
			me.frm.call({
				method: "update_ordered_qty",
				doc: me.frm.doc,
				callback: function() {
					frappe.msgprint(`Finished recalculating PO Qty Ordered, per blanket order line.`);
					console.log('Finished recalculating PO quantities.');
				}
			});
		});

		this.frm.add_custom_button(__('View PO Line Allocations'), function() {
			me.frm.call({
				method: "view_allocated_po_lines",
				doc: me.frm.doc,
				callback: function() {
					frappe.msgprint(`Finished recalculating PO Qty Ordered, per blanket order line.`);
					console.log('Finished recalculating PO quantities.');
				}
			});
		}, "View");

		frappe.run_serially([
			() => {		// First action
				return frappe.db.get_single_value('Buying Settings', 'single_blanket_per_po');
			},
			(single_blanket_per_po) => {  // Second action
				// console.log("Single Blanket per PO? ", single_blanket_per_po);
				if (this.frm.doc.supplier && single_blanket_per_po) {
					this.frm.add_custom_button(__('View Purchase Orders'), function() {
						frappe.set_route('List', 'Purchase Order', {blanket_order: me.frm.doc.name});
					}, "View");
				}
				else if (this.frm.doc.supplier && this.frm.doc.docstatus === 1) {
					this.frm.add_custom_button(__(`<div style="text-decoration: line-through;">
					View Purchase Orders</div>`), function() {
						frappe.msgprint(`In 'Buying Settings', the value for 'Enforce 1 Blanket per PO' is False.<br><br>
						This means the relationship between Blanket PO and Regular PO is purely at the <b>line</b> level.
						<br><br>The code to handle this and 'View Purchase Orders' is not implemented yet.
						`);
					});
				}
			},
			() => {  // Third action
				if (this.frm.doc.supplier && this.frm.doc.docstatus === 1) {
					this.frm.add_custom_button(__("Create Purchase Order"), function(){
						frappe.model.open_mapped_doc({
							method: "erpnext.manufacturing.doctype.blanket_order.blanket_order.make_purchase_order",
							frm: me.frm
						});
					}).addClass("btn-primary");
				}
			}
		]);

		if (this.frm.doc.customer && frm.doc.docstatus === 1) {
			this.frm.add_custom_button(__('View Sales Orders'), function() {
				frappe.set_route('List', 'Sales Order', {blanket_order: me.frm.doc.name});
			});
			this.frm.add_custom_button(__("Create Sales Order"), function(){
				frappe.model.open_mapped_doc({
					method: "erpnext.manufacturing.doctype.blanket_order.blanket_order.make_sales_order",
					frm: me.frm
				});
			}).addClass("btn-primary");
		}

		// Add a button to revert a Blanket Order back into Draft status.
		if (this.frm.doc.docstatus == 1) {
			this.frm.add_custom_button(__('Revert to Draft'), () => this.frm.events._revert_to_draft(this.frm)
			, __())
		}

	} // end of refresh()

});

$.extend(cur_frm.cscript, new erpnext.manufacturing.BlanketOrder({frm: cur_frm}));


frappe.ui.form.on("Blanket Order Item", {
	/*
		* Yes, the line's controller functions are defined here; Child Tables are a 2nd class citizen in Frappe
		* CDT: Current DocType, CDN: Current DocType's name/id
	*/

	items_add: function(frm, cdt, cdn) {
		// Datahenge: This function called when a child row is added.
		// frappe.msgprint(__("New line added to grid for Document {0}", [parent_doc.name]));
		const parent_doc = frm.doc;
		let this_row = locals[cdt][cdn];

		// 1. Default the requirement dates.
		if(parent_doc.from_date) {  // use the parent's value as a default
			this_row.reqd_by_date = parent_doc.from_date;
			refresh_field("reqd_by_date", cdn, "items");
		} else {
			// use the first row's value as default
			frm.script_manager.copy_from_first_row("items", this_row, ["reqd_by_date"]);
		}
		// 2. Default the warehouse
		if(parent_doc.warehouse_default) {
			// Default value = Parent.
			this_row.warehouse = parent_doc.warehouse_default;
			refresh_field("warehouse", cdn, "items");
		}
		else {
			// use the first row's value as default
			frm.script_manager.copy_from_first_row("items", this_row, ["warehouse"]);
		}		
	},

	qty: function(frm, cdt, cdn) {
		let blanket_line = frappe.get_doc(cdt, cdn);
		// 1. Update the line amount.
		recalc_line_amount(cdt, cdn);

		// 2. Update 'qty_in_weight_uom'
		if (blanket_line.uom_buying === blanket_line.uom_weight) {
			blanket_line.qty_in_weight_uom = blanket_line.qty;
		}
		else {
			blanket_line.qty_in_weight_uom = blanket_line.qty * blanket_line.weight_per_unit;
		}
		recalc_line_amount(cdt, cdn);
		recalculate_total_weight(cdt, cdn);
		refresh_field("items");  // Yes, we have to refresh in the context of the Form.

		// For now, I don't have a Stock Quantity field.
		// frappe.model.set_value(cdt, cdn, 'stock_qty', blanket_line.qty * blanket_line.conversion_factor);
	},

	qty_in_weight_uom: function(doc, cdt, cdn) {
		// When 'qty_in_weight_uom' changes, update 'qty'.  Then trigger standard code from there forward.
		// console.log("DEBUG: entered method Blanket Order Line method 'qty_in_weight_uom'");
		let row = frappe.get_doc(cdt, cdn);
		// 1. Update qty
		if (row.uom_buying === row.uom_weight) {
			row.qty = row.qty_in_weight_uom;
			console.log("Making qty = qty_in_weight_uom")
		}
		else {
			row.qty = row.qty_in_weight_uom / row.weight_per_unit;
		}
		recalc_line_amount(cdt, cdn);
		recalculate_total_weight(cdt, cdn);
		refresh_field("items");	
	},

	reqd_by_date: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.reqd_by_date) {
			if(!frm.doc.reqd_by_date) {
				erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "reqd_by_date");
			} else {
				set_schedule_date(frm);
			}
		}
	},

	item_code: (frm, cdt, cdn) => {
		let row = frappe.get_doc(cdt, cdn);
		if (row.item_code) {
			get_item_details(row.item_code)
			.then(data => {
				frappe.model.set_value(cdt, cdn, 'uom', data.stock_uom);
				frappe.model.set_value(cdt, cdn, 'stock_uom', data.stock_uom);
				frappe.model.set_value(cdt, cdn, 'conversion_factor', 1);
				frappe.model.set_value(cdt, cdn, 'description', data.description);
				frappe.model.set_value(cdt, cdn, 'uom_buying', data.purchase_uom || data.stock_uom);
				frappe.model.set_value(cdt, cdn, 'uom_weight', data.weight_uom);
				frappe.model.set_value(cdt, cdn, 'weight_per_unit', data.weight_per_unit);
				if (row.qty) {
					frappe.model.set_value(cdt, cdn, 'total_weight', data.weight_per_unit * row.qty);
				}
				refresh_field("weight_per_unit", cdn, "items");
				// ['stock_uom', 'name', 'weight_per_unit'], as_dict=1)				
			});
		}
	},

	uom: (frm, cdt, cdn) => {
		let row = frappe.get_doc(cdt, cdn);
		if (row.uom) {
			get_item_details(row.item_code, row.uom).then(data => {
				frappe.model.set_value(cdt, cdn, 'conversion_factor', data.conversion_factor);
			});
		}
	},

	rate: (frm, cdt, cdn) => {
		let order_line = frappe.get_doc(cdt, cdn);

		// Scenario 1.  Both UOM are the same:
		if (order_line.uom_weight === order_line.uom_buying) {
			order_line.rate_per_weight_uom = order_line.rate;
		}
		else {
			// Example:  $5.00/lb = $300/drum divided by 60 lbs/drum.
			order_line.rate_per_weight_uom = (order_line.rate / order_line.weight_per_unit);
		}
		recalc_line_amount(cdt, cdn);
		refresh_field("items");  // Yes, we have to refresh in the context of the Form.
	},

	rate_per_weight_uom: (frm, cdt, cdn) => {
		let order_line = frappe.get_doc(cdt, cdn);

		// Scenario 1.  Both UOM are the same:
		if (order_line.uom_weight === order_line.uom_buying) {
			order_line.rate = order_line.rate_per_weight_uom;
		}
		else {
			// Example:  $5.00/lb = $300/drum divided by 60 lbs/drum.
			order_line.rate = (order_line.rate_per_weight_uom * order_line.weight_per_unit);
		}
		recalc_line_amount(cdt, cdn);
		refresh_field("items");  // Yes, we have to refresh in the context of the Form.
	},


	conversion_factor: (frm, cdt, cdn) => {
		let row = frappe.get_doc(cdt, cdn);
		// frappe.model.set_value(cdt, cdn, 'stock_qty', row.qty * row.conversion_factor);
	},

	btn_edit_weight_per_unit: (frm, cdt, cdn) => {
		
		// Prevent button-clicking while other values (qty, uom, qty in weight uom) are in flux.
		if (frm.is_dirty() == 1) {
			frappe.msgprint("This button cannot be used while the Document has unsaved changes.  Save or undo all changes, then try again.")
			return;
		}
		edit_weight_per_unit(frm, cdt, cdn);

		// Datahenge: So far, none of these are working to trigger the Document's save button...
		frm.doc.__unsaved = 1
		this.doc.__unsaved = 1;
	}

});


function get_address_query (doc) {
	if (doc.supplier) {
		// Blanket Purchase Order (PO)			
		return {
			query: 'frappe.contacts.doctype.address.address.address_query',
			filters: { link_doctype: 'Supplier', link_name: doc.supplier }
		};
	}
	if (doc.customer) {
		// Blanket Sales Order (SO)
		return {
			query: 'frappe.contacts.doctype.address.address.address_query',
			filters: { link_doctype: 'Customer', link_name: doc.customer }
		};
	}			
}	

function custom_clear_address (frm) {
	// TODO: This code should only execute when the Supplier or Customer field is touched.
	// Not all the time.

	if (frm.doc.party_billing_address){

		frm.set_value("party_billing_address", "");
		frm.set_value("party_billing_address_display", "");
	}
	frm.set_query("party_billing_address", get_address_query);
}

function default_reqd_by_dates(frm) {
	// Copy the header's From Date to any line that's missing Reqd By Date.
	if(!frm.doc.from_date) return;

	var lines = frm.doc['items'] || [];
	for(var i = 0; i < lines.length; i++) {
		if(!lines[i]['reqd_by_date']) {
			lines[i]['reqd_by_date'] = frm.doc['from_date'];
		}			
	}
	refresh_field('items');
}

function default_line_warehouse(frm) {
	// Copy the header's Warehouse to any line that's missing a warehouse.
	if(!frm.doc.warehouse_default) return;

	var lines = frm.doc['items'] || [];
	for(var i = 0; i < lines.length; i++) {
		if(!lines[i]['warehouse']) {
			lines[i]['warehouse'] = frm.doc['warehouse_default'];
		}			
	}
	refresh_field('items');
}

function get_item_details(item_code, uom=null) {
	if (item_code) {
		return frappe.xcall('erpnext.manufacturing.doctype.blanket_order.blanket_order.get_item_details', {
			item_code,
			uom
		});
	}
}

function recalc_line_amount(cdt, cdn) {
	// 1. Update line amount based on Quantity and Rate.
	var blanket_line = locals[cdt][cdn];
	if (blanket_line.qty && blanket_line.rate) {
		frappe.model.set_value(cdt, cdn, 'line_amount',  blanket_line.qty * blanket_line.rate);
	}
	else {
		frappe.model.set_value(cdt, cdn, 'line_amount', null);
	}
}

function recalculate_total_weight(cdt, cdn) {
	var blanket_line = locals[cdt][cdn];
	if (blanket_line.qty_in_weight_uom) {
		frappe.model.set_value(cdt, cdn, 'total_weight', blanket_line.qty_in_weight_uom);
	}
	else {
		frappe.model.set_value(cdt, cdn, 'total_weight', blanket_line.qty * blanket_line.weight_per_unit);
	}
}


function edit_weight_per_unit(caller_frm, cdt, cdn) {
	
	let blanket_line = locals[cdt][cdn];
	if (blanket_line.docstatus != 0) {
		frappe.msgprint(__("Cannot edit the 'Weight Per Unit' of a Submitted document."));
		return;
	}

	const dlg_title = __('Edit the Weight Per Unit');
	const fields = [
		{
			fieldname: 'new_weight_per_unit',
			read_only: 0,
			fieldtype:'Float',
			label: __('New Weight Per Unit'),
			default: blanket_line.weight_per_unit,
			description: "<b>" + blanket_line.uom_weight + " per " + blanket_line.uom_buying + "</b>",
			reqd: 1
		}
	]
	const mydialog = new frappe.ui.Dialog({
		title: dlg_title,
		fields: fields,
		primary_action: function() {
			const args = mydialog.get_values();
			if(!args) return;
	
			frappe.call({
				method: "set_new_weight_per_uom",
				args: { "new_value":  args.new_weight_per_unit},
				doc: blanket_line,
				callback: function() {
					frappe.msgprint(`Blanket Order Line updated with new conversion.`);
					caller_frm.reload_doc();
					caller_frm.doc.__unsaved = 1;
				}
			});
			mydialog.hide();
		}
	});

	mydialog.show();


}
