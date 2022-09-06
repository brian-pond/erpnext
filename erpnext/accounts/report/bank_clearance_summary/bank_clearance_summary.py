# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
# from frappe.utils import nowdate, getdate

def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_entries(filters)

	return columns, data

def get_columns():
	columns = [
		{
			"label": _("Payment Document Type"),
			"fieldname": "payment_document_type",
			"fieldtype": "Link",
			"options": "Doctype",
			"width": 130
		},
		{
			"label": _("Payment Entry"),
			"fieldname": "payment_entry",
			"fieldtype": "Dynamic Link",
			"options": "payment_document_type",
			"width": 140
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Cheque/Reference No"),
			"fieldname": "cheque_no",
			"width": 120
		},
		{
			"label": _("Clearance Date"),
			"fieldname": "clearance_date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Against Account"),
			"fieldname": "against",
			"fieldtype": "Link",
			"options": "Account",
			"width": 170
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"width": 120
		}]

	return columns


def get_entries(filters):
	"""
	Fetch the data from SQL.
	"""
	# Use read uncommitted, for performance reasons.
	frappe.db.sql("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")

	query = """
		SELECT
			"Journal Entry"					AS source
			,JournalEntry.name
			,JournalEntry.posting_date
			,JournalEntry.cheque_no
			,JournalEntry.clearance_date
			,JournalEntryAccount.against_account
			,JournalEntryAccount.debit - JournalEntryAccount.credit
		FROM
			`tabJournal Entry` 				AS JournalEntry

		INNER JOIN
			`tabJournal Entry Account`		AS JournalEntryAccount
		ON
			JournalEntryAccount.parent = JournalEntry.name

		WHERE 
			JournalEntry.docstatus = 1
		AND JournalEntry.posting_date between %(from_date)s AND %(to_date)s
		AND JournalEntryAccount.account = %(account)s

		UNION ALL

		SELECT
			"Payment Entry"	AS source
			,name
			,posting_date
			,reference_no
			,clearance_date
			,party
			,IF(paid_from = 'Wells Fargo Checking - SF', paid_amount * -1, received_amount)		AS Net
		FROM 
			`tabPayment Entry`		AS PaymentEntry

		WHERE 
			docstatus = 1
		AND ( paid_from = %(account)s OR paid_to = %(account)s )
		AND PaymentEntry.posting_date between %(from_date)s AND %(to_date)s

		UNION ALL

		SELECT
			"Payment Entry Deductions"		AS source
			,PaymentEntry.name
			,posting_date
			,reference_no
			,clearance_date
			,party
			,Deductions.amount		AS Net
		FROM
			`tabPayment Entry Deduction`			AS Deductions

		INNER JOIN 
			`tabPayment Entry`		AS PaymentEntry
		ON
			PaymentEntry.name = Deductions.parent

		WHERE 
			PaymentEntry.docstatus = 1
		AND Deductions.account = %(account)s
		AND PaymentEntry.posting_date between %(from_date)s AND %(to_date)s

		ORDER BY
			posting_date DESC,
			name DESC
		;

	"""

	results = frappe.db.sql(query, filters, as_list=1)

	# Re-enable the default Transactional Isolation Level
	frappe.db.sql("SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;")

	return results
