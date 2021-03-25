// Blanket Order Item: Client Actions

frappe.ui.form.on("Blanket Order Item", {

	// When quantity changes, update Line Amount
	qty: function(frm,cdt,cdn) {
		var me = this;

		frm.doc.line_amount = this * frm.doc.rate;
		// me.frm.set_value("line_amount", company_currency);
	}
});
