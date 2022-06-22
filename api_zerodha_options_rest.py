# Author - Karan Parmar
# Author - Nagavishnu B K

"""
Zerodha REST API

- Auto login to Zerodha account
- get account info
- get balance
- place orders in options
- get expiries for a ticker
- query order
- cancel open order
"""

# Importing built-in libraries
import os, json, pytz, time
from datetime import datetime, date

# Importing third-party libraries
import requests												# pip install requests
from kiteconnect import KiteConnect							# pip install kiteconnect
import undetected_chromedriver as uc 						# pip install undetected_chromedriver
import pyotp												# pip install pyotp
from selenium.webdriver.support.ui import WebDriverWait		# pip install selenium
from selenium.webdriver.common.by import By

class ZerodhaOptionsRESTAPI:

	ID = "VT_API_REST_ZERODHA_OPTIONS"
	NAME = "Zerodha options REST API"
	AUTHOR = "Variance Technologies pvt. ltd."
	EXCHANGE = "SMART"
	BROKER = "ZERODHA"
	MARKET = "OPTIONS"

	TIMEZONE = "Asia/Kolkata"
	TOKEN_PATH = "zerodha_token.json"

	_months = ["JAN","FEB","MAR","APR","MAY","JUN","JULY","AUG","SEP","OCT","NOV","DEC"]
	_chrome_version = 102

	def __init__(self, creds:dict):

		self.CREDS = creds

		self.AUTO_CONNECT = creds.get("auto_connect")

	# Private methods
	def _auto_generate_access_token(self) -> str:
		"""
		Auto generates access token that valid for 12 AM midnight IST\n
		Requires username, password, totp key for a day, request token changes everytime user requests a token\n
		Returns str that represents access token\n
		"""
		self.client = KiteConnect(api_key=self.CREDS['api_key'])
		driver = uc.Chrome(version_main = self._chrome_version)
		driver.get(self.client.login_url())

		# Filling username field
		login_id = WebDriverWait(driver, 10).until(lambda x: x.find_element(by=By.XPATH, value='//*[@id="userid"]'))
		login_id.send_keys(self.CREDS['username'])

		# Filling password field
		pwd = WebDriverWait(driver, 10).until(lambda x: x.find_element(by=By.XPATH, value='//*[@id="password"]'))
		pwd.send_keys(self.CREDS['password'])

		# Clicking login button
		submit = WebDriverWait(driver, 10).until(lambda x: x.find_element(by=By.XPATH, value='//*[@id="container"]/div/div/div[2]/form/div[4]/button'))
		submit.click()

		time.sleep(1)

		# Filling TOTP
		totp = WebDriverWait(driver, 10).until(lambda x: x.find_element(by=By.XPATH, value='//*[@id="totp"]'))
		authkey = pyotp.TOTP(self.CREDS['totp_key'])
		totp.send_keys(authkey.now())
		
		# Clicking authorize button
		continue_btn = WebDriverWait(driver, 10).until(lambda x: x.find_element(by=By.XPATH, value='//*[@id="container"]/div/div/div[2]/form/div[3]/button'))
		continue_btn.click()

		time.sleep(5)

		# Parsing request token
		url = driver.current_url
		initial_token = url.split('request_token=')[1]
		self.REQUEST_TOKEN = initial_token.split('&')[0]

		driver.close()

		# Fetching access token
		session = self.client.generate_session(self.REQUEST_TOKEN, self.CREDS['api_secret'])
		return session['access_token']

	def _generate_access_token(self) -> str:
		"""
		Generates access token that valid for 12 AM midnight IST\n
		Requires a request token for a day, request token changes everytime user requests a token\n
		Returns str that represents access token\n
		"""
		self.client = KiteConnect(api_key=self.CREDS['api_key'])
		url = self.client.login_url()
		print("Generate request token using this url")
		print(url)
		self.REQUEST_TOKEN = input("Enter request token : ")
		session = self.client.generate_session(self.REQUEST_TOKEN, self.CREDS['api_secret'])
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

	def _get_options_symbol(self, symbol:str, expiry:date, strike_price:int, call_put:str, is_monthly_expiry:bool=False) -> str:
		"""
		Returns Zerodha options symbol for trading\n
		NOTE This symbol has been changed 6 times in last 2 years, I don't know why but Zerodha API devs the options symbol\n
		so, this symbol combination may or may not work in future, so kindly maintain this method\n
		"""
		_year = expiry.year
		_month = expiry.month
		_day = expiry.day
		_cp = "CE" if call_put.lower() == 'call' else "PE"

		# Symbol if expiry is weekly
		if not is_monthly_expiry:
			# _ex = str(_year)[-2:] + f"{_month:02d}" + str(_day)					# NIFTY22061616100CE
			_ex = str(_year)[-2:] + f"{_month}" + str(_day)							# NIFTY2261616100CE
			# _ex = str(_year)[-2:] + f"{self._months[_month-1]}" + str(_day)		# NIFTY22JUN1616100CE
		
		# Symbol if expiry is monthly
		else:
			_ex = str(_year[-2:]) + f"{self._months[_month-1]}"						# NIFTY22JUN16100CE
		
		options_symbol = f"{symbol.upper()}{_ex}{strike_price}{_cp}"
		return options_symbol

	# Public methods
	def connect(self) -> None:
		"""
		Connect the system with Zerodha\n
		To connect to Zerodha broker, user require an request token, this request token used to generate access token\n
		Access token is constant during a day and user needs to regenerate after 12PM midnight\n
		It is advisable to connect the system with broker before market open\n
		Returns :\n
			status of connection with broker\n
		"""
		# IF TOKEN NOT EXISTS OR EXPIRED THEN GENERATE A NEW TOKEN
		if (not os.path.exists(self.TOKEN_PATH)) or self._is_token_expired():
			
			# AUTO CONNECT AND GENERATE ACCESS TOKEN
			if self.AUTO_CONNECT:
				token = self._auto_generate_access_token()
				self._save_token(token)
				return self.connect()
			
			# MANUALLY CONNECT AND GENERATE ACCESS TOKEN
			else:
				token = self._generate_access_token()
				self._save_token(token)
				return self.connect()
		
		else:
			# IF TOKEN IS NOT EXPIRED THEN USE THE CURRENT TOKEN
			# NOTE IF USING THE LATEST TOKEN STILL USER CAN NOT CONNECT THEN REGENERATE TOKEN
			token = self._read_token()
			self.ACCESS_TOKEN = token['access_token']
			try:
				self.client = KiteConnect(self.CREDS['api_key'], self.ACCESS_TOKEN)
				self.client.profile()

			except Exception:
				return self.connect()

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
		return self.client.margins(segment)['available']['live_balance']

	def get_expiries(self, symbol:str) -> list:
		"""
		Get expiries for a symbol\n
		"""
		url = "https://www.nseindia.com/api/option-chain-indices"

		params = {
			"symbol":symbol
		}
		headers = {
			"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
			"Connection":"keep-alive",
			"Upgrade-Insecure-Requests":"1",
			"User-Agent":"Mozilla/5.0 (X11; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0"
		}

		expiries = requests.get(url, params=params, headers=headers).json()['records']['expiryDates']
		return [datetime.strptime(i, "%d-%b-%Y").date() for i in expiries]
	
	def place_order(
			self, 
			symbol:str,
			expiry:date,
			strike_price:int,
			call_put:str,
			side:str,
			quantity:int,
			order_type:str="MARKET",
			price:float=None,
			**options,
		) -> int:
		"""
		Places options order in Zerodha account\n
		"""
		
		options_symbol = self._get_options_symbol(symbol, expiry, strike_price, call_put, options.get('is_monthly_expiry', False))
		# print(options_symbol)

		body = {
			"variety":options.get('variety',self.client.VARIETY_REGULAR),
			"exchange":options.get('exchange',self.client.EXCHANGE_NFO),
			"tradingsymbol":options_symbol,
			"transaction_type":side.upper(),
			"quantity":quantity,
			"product":options.get('product',self.client.PRODUCT_MIS),
			"order_type":order_type.upper(),
			"validity":self.client.VALIDITY_DAY
		}
		if order_type.lower() == 'limit':
			body['trigger_price'] = price
		return self.client.place_order(**body)

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

	with open("credentials.json") as f:
		creds = json.load(f)
		f.close()

	api = ZerodhaOptionsRESTAPI(creds=creds)
	api.connect()

	# NOTE Get account info
	# account_info = api.get_account_info()
	# print(account_info)
	
	# NOTE Get account balance
	# balance = api.get_account_balance('equity')
	# print(balance)

	# NOTE Get expiries
	# symbol = "NIFTY"
	# expiries = api.get_expiries(symbol=symbol)
	# print(expiries)

	# NOTE Get zerodha options symbol
	# symbol = "NIFTY"
	# expiry = date(2022,6,16)
	# strike_price = 16100
	# call_put = "call"
	# is_monthly_expiry = False
	# options_symbol = api._get_options_symbol(
	# 	symbol=symbol,
	# 	expiry=expiry,
	# 	strike_price=strike_price,
	# 	call_put=call_put,
	# 	is_monthly_expiry=is_monthly_expiry,
	# )
	# print(options_symbol)

	# NOTE Place order
	# symbol = "NIFTY"
	# expiry = date(2022,6,16)
	# strike_price = 16100
	# call_put = "call"
	# side = "buy"
	# quantity = 1
	# order_type = "MARKET"
	# price = None
	# order_id = api.place_order(
	# 	symbol=symbol,
	# 	expiry=expiry,
	# 	strike_price=strike_price,
	# 	call_put=call_put,
	# 	side=side,
	# 	quantity=quantity,
	# 	order_type=order_type,
	# 	price=price,
	# )
	# print(order_id)

	# NOTE Query order
	# order_id = 151220000000000
	# query = api.query_order(order_id=order_id)
	# print(query)

	# NOTE Cancel order
	# order_id = 220125003110635
	# api.cancel_order(order_id=order_id)
	