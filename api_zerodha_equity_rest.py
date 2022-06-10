# Author - Karan Parmar

"""
Zerodha REST API

- Auto login to Zerodha account
- get account info
- get balance
- place orders in equities
- query order
- cancel open order
"""

# Importing built-in libraries
import os, json, pytz
from datetime import datetime, date

# Importing third-party libraries
import requests						# pip install requests
from kiteconnect import KiteConnect	# pip install kiteconnect

class ZerodhaEquityRESTAPI:

	ID = "VT_API_REST_ZERODHA_EQUITY"
	NAME = "Zerodha Equity REST API"
	AUTHOR = "Variance Technologies pvt. ltd."
	EXCHANGE = "SMART"
	BROKER = "ZERODHA"
	MARKET = "OPTIONS"

	TIMEZONE = "Asia/Kolkata"
	TOKEN_PATH = "zerodha_token.json"

	def __init__(self, creds:dict):

		self.CREDS = creds

	# Private methods
	def _generate_access_token(self) -> str:
		"""
		Generates access token that valid for 12 AM midnight IST\n
		Requires a request token for a day, request token changes everytime user requests a token\n
		Returns str that represents access token\n
		"""
		url = self.api.login_url()
		print("Generate request token using this url")
		print(url)
		self.REQUEST_TOKEN = input("Enter request token : ")
		session = self.api.generate_session(self.REQUEST_TOKEN, self.CREDS['api_secret'])
		return session['access_token']

	def _read_token(self) ->  dict:
		"""
		Reads the token from token file\n
		"""
		with open(self.TOKEN_PATH) as f:
			token = json.load(f)
			f.close()
		return token
	
	def _is_token_expired(self) -> bool:
		"""
		Checks if the token is expired\n
		if current date and token generation date doesn't match that means token is expired\n
		"""
		token = self._read_token()
		generation_date = datetime.strptime(token['date'],"%Y-%m-%d")
		return datetime.now(pytz.timezone(self.TIMEZONE)).date() > generation_date.date()

	def _save_token(self,access_token:str) -> None:
		"""
		Save the token in json format with date\n
		"""
		token = {
			'date':datetime.now(pytz.timezone(self.TIMEZONE)).strftime("%Y-%m-%d"),
			'request_token':self.REQUEST_TOKEN,
			'access_token':access_token
		}
		with open(self.TOKEN_PATH,'w') as f:
			json.dump(token,f,indent=4)
			f.close()

	# Public methods
	def connect(self) -> None:
		"""
		Connect the bot with Zerodha\n
		To connect to Zerodha broker, user require an request token, this request token used to generate access token\n
		Access token is constant during a day and user needs to regenerate after 12PM midnight\n
		It is advisable to connect the bot with broker before market open\n
		Returns :\n
			status of connection with broker\n
		"""
		# IF TOKEN NOT EXISTS OR EXPIRED THEN GENERATE A NEW TOKEN
		if (not os.path.exists(self.TOKEN_PATH)) or self._is_token_expired():
			token = self._generate_access_token()
			self._save_token(token)
			return self.connect()
		
		else:
			# IF TOKEN IS NOT EXPIRED THEN USE THE CURRENT TOKEN
			# NOTE IF USING THE LATEST TOKEN STILL USER CAN NOT CONNECT THEN REGENERATE TOKEN
			token = self._read_token()
			self.ACCESS_TOKEN = token['access_token']
			try:
				self.client = KiteConnect(self.API_KEY,self.ACCESS_TOKEN)
				return True
			except Exception:
				return False

	def get_account_info(self) -> dict:
		"""
		Returns account information\n
		"""
		return self.client.profile()

	def get_account_balance(self, segment:str=None) -> float:
		"""
		Returns account balance for segment\n
		segment : str = (default value None) segment of the account. ie. equity, futures, options\n 
		"""
		return self.api.margins(segment)['available']['live_balance']

	def place_order(
			self, 
			symbol:str,
			side:str,
			quantity:int,
			order_type:str="MARKET",
			price:float=None,
			**options,
		) -> int:
		"""
		Places Equity order in Zerodha account\n
		"""
		body = {
			"variety":options.get('variety',self.api.VARIETY_REGULAR),
			"exchange":options.get('exchange',self.api.EXCHANGE_NSE),
			"tradingsymbol":symbol,
			"transaction_type":side.upper(),
			"quantity":quantity,
			"product":options.get('product',self.api.PRODUCT_CNC),
			"order_type":order_type.upper(),
			"validity":self.api.VALIDITY_DAY
		}
		if order_type.lower() == 'limit':
			body['trigger_price'] = price
		return self.api.place_order(**body)

	def query_order(self, order_id:int) -> dict:
		"""
		Get order information\n
		"""
		return self.client.order_history(order_id)[-1]

	def cancel_order(self, order_id:int) -> None:
		"""
		Cancel open order\n
		"""
		variety = self.query_order(order_id)['variety']
		return self.client.cancel_order(variety, order_id)

if __name__ == "__main__":

	with open("creds_zerodha.json") as f:
		creds = json.load(f)
		f.close()

	api = ZerodhaEquityRESTAPI(creds=creds)
	# api.connect()

	# NOTE Get account info
	# account_info = api.get_account_info()
	# print(account_info)
	
	# NOTE Get account balance
	# balance = api.get_account_balance('equity')
	# print(balance)

	# NOTE Query order
	# order_id = 220125003110635
	# query = api.query_order(order_id=order_id)
	# print(query)

	# NOTE Cancel order
	# order_id = 220125003110635
	# api.cancel_order(order_id=order_id)
	