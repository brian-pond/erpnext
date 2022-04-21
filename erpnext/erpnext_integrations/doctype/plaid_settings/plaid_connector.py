# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# Datahenge: Updated for plaid + Python 3.9

import plaid
import requests

# from plaid.exceptions import ApiException  # Python 3.9
# from plaid.errors import APIError, ItemError, InvalidRequestError

import frappe
from frappe import _


class PlaidConnector():
	def __init__(self, access_token=None):
		self.access_token = access_token
		self.settings = frappe.get_single("Plaid Settings")
		self.products = ["auth", "transactions"]
		self.client_name = frappe.local.site
		self.client = plaid.Client(
			client_id=self.settings.plaid_client_id,
			secret=self.settings.get_password("plaid_secret"),
			environment=self.settings.plaid_env,
			api_version="2020-09-14"
		)

	def get_access_token(self, public_token):
		if public_token is None:
			frappe.log_error(_("Public token is missing for this bank"), _("Plaid public token error"))
		response = self.client.Item.public_token.exchange(public_token)
		access_token = response["access_token"]
		return access_token

	def get_token_request(self, update_mode=False):
		country_codes = ["US", "CA", "FR", "IE", "NL", "ES", "GB"] if self.settings.enable_european_access else ["US", "CA"]
		args = {
			"client_name": self.client_name,
			# only allow Plaid-supported languages and countries (LAST: Sep-19-2020)
			"language": frappe.local.lang if frappe.local.lang in ["en", "fr", "es", "nl"] else "en",
			"country_codes": country_codes,
			"user": {
				"client_user_id": frappe.generate_hash(frappe.session.user, length=32)
			}
		}

		if update_mode:
			args["access_token"] = self.access_token
		else:
			args.update({
				"client_id": self.settings.plaid_client_id,
				"secret": self.settings.plaid_secret,
				"products": self.products,
			})

		return args

	def get_link_token(self, update_mode=False):
		token_request = self.get_token_request(update_mode)

		try:
			response = self.client.LinkToken.create(token_request)
		except plaid.ApiException as ex:
			frappe.log_error(frappe.get_traceback(), _("Plaid API exception"))
			frappe.throw(_(str(ex)), title=_("Authentication Failed"))
		else:
			return response["link_token"]

	def auth(self):
		try:
			self.client.Auth.get(self.access_token)
		except plaid.ApiException  as ex:
			if ex.code == "PLANNED_MAINTENANCE":
				pass
			if ex.code == "ITEM_LOGIN_REQUIRED":
				pass
		except requests.Timeout:
			pass
		except Exception as ex:
			frappe.log_error(frappe.get_traceback(), _("Plaid authentication error"))
			frappe.throw(_(str(ex)), title=_("Authentication Failed"))

	def get_transactions(self, start_date, end_date, account_id=None):
		self.auth()
		kwargs = dict(
			access_token=self.access_token,
			start_date=start_date,
			end_date=end_date
		)
		if account_id:
			kwargs.update(dict(account_ids=[account_id]))

		try:
			response = self.client.Transactions.get(**kwargs)
			transactions = response["transactions"]
			while len(transactions) < response["total_transactions"]:
				response = self.client.Transactions.get(self.access_token, start_date=start_date, end_date=end_date, offset=len(transactions))
				transactions.extend(response["transactions"])
			return transactions
		except ItemError as e:
			raise e
		except Exception:
			frappe.log_error(frappe.get_traceback(), _("Plaid transactions sync error"))
