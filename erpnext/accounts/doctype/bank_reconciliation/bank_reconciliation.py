# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, nowdate, fmt_money
from frappe import msgprint, _
from frappe.model.document import Document

form_grid_templates = {
	"journal_entries": "templates/form_grid/bank_reconciliation_grid.html"
}

class BankReconciliation(Document):

	def get_payment_entries(self):
		if not (self.from_date and self.to_date):
			frappe.throw(_("From Date and To Date are Mandatory"))

		if not self.account:
			frappe.throw(_("Account is mandatory to get payment entries"))

		condition = ""
		if not self.include_reconciled_entries:
			condition = "and (clearance_date IS NULL or clearance_date='0000-00-00')"

		journal_entries = frappe.db.sql("""
			select
				"Journal Entry" as payment_document, t1.name as payment_entry,
				t1.cheque_no as cheque_number, t1.cheque_date,
				sum(t2.debit_in_account_currency) as debit, sum(t2.credit_in_account_currency) as credit,
				t1.posting_date, t2.against_account, t1.clearance_date, t2.account_currency
			from
				`tabJournal Entry` t1, `tabJournal Entry Account` t2
			where
				t2.parent = t1.name and t2.account = %(account)s and t1.docstatus=1
				and t1.posting_date >= %(from)s and t1.posting_date <= %(to)s
				and ifnull(t1.is_opening, 'No') = 'No' {condition}
			group by t2.account, t1.name
			order by t1.posting_date ASC, t1.name DESC
		""".format(condition=condition), {"account": self.account, "from": self.from_date, "to": self.to_date}, as_dict=1)

		if self.bank_account:
			condition += 'and bank_account = %(bank_account)s'

		payment_entries = frappe.db.sql("""
			select
				"Payment Entry" as payment_document, name as payment_entry,
				reference_no as cheque_number, reference_date as cheque_date,
				if(paid_from=%(account)s, paid_amount, 0) as credit,
				if(paid_from=%(account)s, 0, received_amount) as debit,
				posting_date, ifnull(party,if(paid_from=%(account)s,paid_to,paid_from)) as against_account, clearance_date,
				if(paid_to=%(account)s, paid_to_account_currency, paid_from_account_currency) as account_currency
			from `tabPayment Entry`
			where
				(paid_from=%(account)s or paid_to=%(account)s) and docstatus=1
				and posting_date >= %(from)s and posting_date <= %(to)s
				{condition}
			order by
				posting_date ASC, name DESC
		""".format(condition=condition), {"account": self.account, "from":self.from_date,
				"to": self.to_date, "bank_account": self.bank_account}, as_dict=1)


		pos_sales_invoices, pos_purchase_invoices = [], []
		if self.include_pos_transactions:
			pos_sales_invoices = frappe.db.sql("""
				select
					"Sales Invoice Payment" as payment_document, sip.name as payment_entry, sip.amount as debit,
					si.posting_date, si.customer as against_account, sip.clearance_date,
					account.account_currency, 0 as credit
				from `tabSales Invoice Payment` sip, `tabSales Invoice` si, `tabAccount` account
				where
					sip.account=%(account)s and si.docstatus=1 and sip.parent = si.name
					and account.name = sip.account and si.posting_date >= %(from)s and si.posting_date <= %(to)s
				order by
					si.posting_date ASC, si.name DESC
			""", {"account":self.account, "from":self.from_date, "to":self.to_date}, as_dict=1)

			pos_purchase_invoices = frappe.db.sql("""
				select
					"Purchase Invoice" as payment_document, pi.name as payment_entry, pi.paid_amount as credit,
					pi.posting_date, pi.supplier as against_account, pi.clearance_date,
					account.account_currency, 0 as debit
				from `tabPurchase Invoice` pi, `tabAccount` account
				where
					pi.cash_bank_account=%(account)s and pi.docstatus=1 and account.name = pi.cash_bank_account
					and pi.posting_date >= %(from)s and pi.posting_date <= %(to)s
				order by
					pi.posting_date ASC, pi.name DESC
			""", {"account": self.account, "from": self.from_date, "to": self.to_date}, as_dict=1)

		entries = sorted(list(payment_entries) + list(journal_entries + list(pos_sales_invoices) + list(pos_purchase_invoices)),
			key=lambda k: k['posting_date'] or getdate(nowdate()))

		self.set('payment_entries', [])
		self.total_amount = 0.0
		self.total_debits = 0.0
		self.total_credits = 0.0

		for d in entries:
			row = self.append('payment_entries', {})

			amount = flt(d.get('debit', 0)) - flt(d.get('credit', 0))

			formatted_amount = fmt_money(abs(amount), 2, d.account_currency)
			d.amount = formatted_amount + " " + (_("Dr") if amount > 0 else _("Cr"))

			self.total_debits += flt(d.get('debit', 0))
			self.total_credits += flt(d.get('credit', 0))
			d.pop("credit")
			d.pop("debit")
			d.pop("account_currency")
			row.update(d)
			self.total_amount += flt(amount)


	def update_clearance_date(self):
		clearance_date_updated = False
		for d in self.get('payment_entries'):
			# Spectrum Fruits: When the 'is_cleared' box is marked, set the clearance date to the From Date.
			if d.is_cleared and not d.clearance_date:
				d.clearance_date = self.to_date

			if d.clearance_date:
				if not d.payment_document:
					frappe.throw(_("Row #{0}: Payment document is required to complete the transaction"))

				if d.cheque_date and getdate(d.clearance_date) < getdate(d.cheque_date):
					frappe.throw(_("Row #{0}: Clearance date {1} cannot be before Cheque Date {2}")
						.format(d.idx, d.clearance_date, d.cheque_date))

			if d.clearance_date or self.include_reconciled_entries:
				if not d.clearance_date:
					d.clearance_date = None

				payment_entry = frappe.get_doc(d.payment_document, d.payment_entry)
				payment_entry.db_set('clearance_date', d.clearance_date)

				clearance_date_updated = True

		if clearance_date_updated:
			self.get_payment_entries()
			msgprint(_("Clearance Date updated"))
		else:
			msgprint(_("Clearance Date not mentioned"))

		self.update_amount_reconciled_on_date()  # Spectrum Fruits

	@frappe.whitelist()
	def update_amount_reconciled_on_date(self):
		"""
		Example:  All transactions with a clearance date of July 12th,
				for GL account = 'Wells Fargo Checking - SF'
		"""

		# Spectrum Fruits, October 13th : Added Payment Entry Deductions to the calculations.
		query = """
		SELECT
			'JournalEntry'											AS document_type
			,sum(JournalEntryAccount.debit_in_account_currency)		AS cleared_debit
			,sum(JournalEntryAccount.credit_in_account_currency)	AS cleared_credit
		FROM
			`tabJournal Entry Account`		AS JournalEntryAccount
		INNER JOIN
			`tabJournal Entry`		AS JournalEntry
		ON
			JournalEntry.name = JournalEntryAccount.parent 
		AND JournalEntry.docstatus = 1
		AND JournalEntry.clearance_date =  %(clearance_date)s
		WHERE
			JournalEntryAccount.account = %(ledger_account)s
		AND ifnull(JournalEntry.is_opening, 'No') = 'No'
		
		UNION ALL

		SELECT
			'Payment Entry'		AS document_type
			,SUM(CASE		WHEN paid_from <> %(ledger_account)s THEN paid_amount ELSE 0 END) 			AS debit 
			,SUM(CASE 		WHEN paid_from = %(ledger_account)s THEN received_amount ELSE 0 END) 		AS credit						
		FROM
			`tabPayment Entry`		AS PaymentEntry

		WHERE
			( PaymentEntry.paid_to = %(ledger_account)s OR PaymentEntry.paid_from = %(ledger_account)s )
		AND clearance_date = %(clearance_date)s
		AND docstatus = 1

		UNION ALL

		SELECT
			'Payment Entry Deduction'		AS document_type
			,SUM(CASE	WHEN amount > 0 THEN amount ELSE 0 END) 		AS debit 
			,SUM(CASE	WHEN amount < 0 THEN amount ELSE 0 END) 		AS credit						
		
		FROM	
			`tabPayment Entry Deduction`		AS PaymentEntryDeduction

		INNER JOIN
			`tabPayment Entry`		AS PaymentEntry
		ON 
			( PaymentEntry.paid_to = %(ledger_account)s OR PaymentEntry.paid_from = %(ledger_account)s )
		AND PaymentEntry.clearance_date = %(clearance_date)s
		AND PaymentEntry.docstatus = 1
		AND PaymentEntry.name = PaymentEntryDeduction.parent
		
		WHERE
			PaymentEntryDeduction.account = %(ledger_account)s
		"""

		sql_results = frappe.db.sql(query, values={"ledger_account": self.account,
		                                           "clearance_date": self.to_date}, as_dict=True)

		total_debits = 0
		total_credits = 0

		for each_row in sql_results:
			total_debits += each_row['cleared_debit'] or 0.00
			total_credits += each_row['cleared_credit'] or 0.00

		# Spectrum Fruits additions
		self.total_cleared_debits = total_debits
		self.total_cleared_credits = total_credits
		self.save()
