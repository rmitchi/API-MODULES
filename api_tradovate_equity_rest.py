# Author - Karan Parmar

"""
TRADOVATE EQUITY REST API
"""

# Importing built-in libraries
import os, json
from datetime import datetime, timedelta

# Importing third-party libraries
import requests						# pip install requests
import pandas as pd					# pip install pandas


class TradovateAuth:
	
	LIVE_ENDPOINT = "https://live.tradovateapi.com"
	SIMULATION_ENDPOINT = "https://demo.tradovateapi.com"

	API_VERSION = "v1"

	_headers = {
		'Content-Type': 'application/json',
		'Accept': 'application/json',
	}

	# Helper methods
	@staticmethod
	def _read_json_file(filePath:str) -> dict:
		"""
		Parse and read json file\n
		"""
		with open(filePath) as f:
			data = json.load(f)
			f.close()
		return data

	# Private methods
	def _get_endpoint(self) -> str:
		"""
		Gets the raw endpoint from REST api\n
		"""
		return self.ENDPOINT + '/' + self.API_VERSION

	def _get_headers(self):
		"""
		Get headers for REST api to send as sensetive data\n
		"""
		headers = self._headers.copy()
		headers['Authorization'] = 'Bearer ' + self.ACCESS_TOKEN
		return headers

	def _is_token_expired(self,expiryDate:str) -> bool:
		"""
		Check if the generated token is expired or not\n
		expiryDate : str = datetime of the token follows (yyyy-mm-ddTHH:MM:SSz)\n
		"""
		expiry = datetime.strptime(expiryDate[:-5],"%Y-%m-%dT%H:%M:%S")
		utcTime = datetime.strptime(datetime.now().utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"%Y-%m-%dT%H:%M:%S")
		return utcTime >= (expiry - timedelta(minutes=10))

	def _generate_access_token(self) -> None:
		"""
		Generates access token\n
		NOTE This token will be valid for 80 minutes from now\n 
		"""
		# AUTHENTICATE
		try:
			endpoint = self._get_endpoint() + '/auth/accesstokenrequest'

			params = {
				'name':self.USERNAME,
				'password':self.PASSWORD,
				'appId':self.APP_ID,
				'appVersion':self.APP_VERSION,
				'deviceId':self.UUID,
				'cid':self.API_KEY,
				'sec':self.API_SECRET
			}
			
			response = requests.post(endpoint,json=params,headers=self.headers)
			token = response.json()

			self._save_token(token)

		except Exception as e:
			_ = f"error connecting to broker, {e}"
			raise Exception(_)

	# Public methods
	def set_user_credentials(self, creds:dict) -> None:
		"""
		Sets user's credential info\n
		"""
		self.TOKEN_PATH = "tradovate_access_token.json"
		self.USERNAME = creds['username']
		self.PASSWORD = creds['password']
		self.APP_ID = creds['app_id']
		self.APP_VERSION = creds['app_version']
		self.API_KEY = creds['api_key']
		self.API_SECRET = creds['api_secret']
		self.UUID = creds['uuid']
		self.ENDPOINT = self.SIMULATION_ENDPOINT if self.CREDS['account_type'].lower() == 'demo' else self.LIVE_ENDPOINT

	def set_account(self):
		"""
		Set account ID and SPEC\n
		"""
		accountInfo = self.get_account()
		self.ACCOUNT_ID, self.ACCOUNT_SPEC = accountInfo['id'], accountInfo['name']

	def login(self) -> None:
		"""
		Log into tradovate account with access token\n
		"""
		if os.path.exists(self.TOKEN_PATH):
			token = self._read_json_file(self.TOKEN_PATH)

			# CHECK IF EXPIRED
			if self.is_token_expired(token['expirationTime']):
				self.generate_access_token()
				try:
					self.ACCESS_TOKEN = token['accessToken']
					self.MD_ACCESS_TOKEN = token['mdAccessToken']
					self.set_account()

				except Exception:
					return self.login()

			self.ACCESS_TOKEN = token['accessToken']

		else:
			self._generate_access_token()
			return self.login()

class TradovateEquityRESTAPI(TradovateAuth):

	ID = "VT_TRADOVATE_EQUITY_API_REST"
	AUTHOR = "Variance Technologies"
	EXCHANGE = "SMART"
	BROKER = "TRADOVATE"
	MARKET = "EQUITY"

	def __init__(self, creds:dict):

		self.CREDS = creds

		self.set_user_credentials(creds)

	# Public methods
	def connect(self) -> None:
		"""
		Connect to Tradovate equity account\n
		"""
		self.login()

	def get_candle_data(self, symbol:str, timeframe:str, period:str='1d') -> pd.DataFrame:
		"""
		Get realtime candlestick data\n
		symbol		: str 	= 	symbol of the ticker\n
		timeframe	: str 	= 	timeframe of the candles\n
		period		: str	=	period of the data\n
		"""
		pass

	def place_order(self, symbol:str, side:str, quantity:int, orderType:str='MARKET', price:float=None) -> int:
		"""
		Places order in connected account\n
		symbol		: str	= symbol of the ticker\n
		side		: str	= side of the order. ie. buy, sell\n
		quantity	: int 	= no of shares to execute as quantity\n
		orderType	: str	= order type. ie. MARKET, LIMIT, STOP...\n
		price		: float	= price to place limit or stop\n
		"""
		pass

	def place_oco_order(self) -> tuple[int, int]:
		"""
		"""
		pass

	def place_oso_order(self) -> tuple[int, int]:
		"""
		"""
		pass

	def cancel_order(self, symbol:str, orderId:int) -> None:
		"""
		Cancels open working order\n
		"""
		pass

	def query_order(self, symbol:str, orderId:int) -> dict:
		"""
		Get order information\n
		"""
		pass

if __name__ == "__main__":

	creds = {
		"account_type":"demo"
	}

	api = TradovateEquityRESTAPI(creds=creds)
	api.connect()

	# Get candle data