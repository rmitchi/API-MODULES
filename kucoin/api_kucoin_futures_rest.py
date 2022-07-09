# Author - Karan Parmar

"""
Kucoin FUTURES REST API
"""

# Importing built-in libraries
import json, time, pytz
from datetime import datetime
import hmac, base64, hashlib
from uuid import uuid1
from urllib.parse import urljoin

# Importing third-party libraries
import pandas as pd					# pip install pandas
import requests						# pip install requests

class KucoinFuturesAPIREST:

	ID = "VT_KUCOIN_FUTURES_API_REST"
	AUTHOR = "Variance Technologies"
	EXCHANGE = "Kucoin"
	BROKER = "Kucoin"
	MARKET = "FUTURES"

	TIMEZONE = "UTC"

	LIVE_ENDPOINT = 'https://api-futures.kucoin.com'
	SANDBOX_ENDPOINT = 'https://api-sandbox-futures.kucoin.com'

	is_v1_api = False

	def __init__(self, creds:dict):
		
		self.CREDS = creds

		if self.CREDS['account_type'].lower() in ['sandbox','testnet','test','demo']:
			self.url = self.SANDBOX_ENDPOINT
		else:
			self.url = self.LIVE_ENDPOINT

	# Private methods
	def _request(self, method, uri, timeout=5, auth=True, params=None):
		uri_path = uri
		data_json = ''
		if method in ['GET', 'DELETE']:
			if params:
				strl = []
				for key in sorted(params):
					strl.append("{}={}".format(key, params[key]))
				data_json += '&'.join(strl)
				uri += '?' + data_json
				uri_path = uri
		else:
			if params:
				data_json = json.dumps(params)

				uri_path = uri + data_json

		headers = {}
		if auth:
			now_time = int(time.time()) * 1000
			str_to_sign = str(now_time) + method + uri_path
			sign = base64.b64encode(hmac.new(self.CREDS['api_secret'].encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
			if self.is_v1_api:
				headers = {
					"KC-API-SIGN": sign,
					"KC-API-TIMESTAMP": str(now_time),
					"KC-API-KEY": self.CREDS['api_key'],
					"KC-API-PASSPHRASE": self.CREDS['passphrase'],
					"Content-Type": "application/json"
				}
			else:
				passphrase = base64.b64encode(
					hmac.new(self.CREDS['api_secret'].encode('utf-8'), self.CREDS['passphrase'].encode('utf-8'), hashlib.sha256).digest())
				headers = {
					"KC-API-SIGN": sign,
					"KC-API-TIMESTAMP": str(now_time),
					"KC-API-KEY": self.CREDS['api_key'],
					"KC-API-PASSPHRASE": passphrase,
					"Content-Type": "application/json",
					"KC-API-KEY-VERSION": "2"
				}
		headers["User-Agent"] = "kucoin-python-sdk/" + '1.0.0' #version
		url = urljoin(self.url, uri)

		if method in ['GET', 'DELETE']:
			response_data = requests.request(method, url, headers=headers, timeout=timeout)
		else:
			response_data = requests.request(method, url, headers=headers, data=data_json, timeout=timeout)
		return self.check_response_data(response_data)
	
	@staticmethod
	def check_response_data(response_data):
		if response_data.status_code == 200:
			try:
				data = response_data.json()
			except ValueError:
				raise Exception(response_data.content)
			else:
				if data and data.get('code'):
					if data.get('code') == '200000':
						if data.get('data'):
							return data['data']
						else:
							return data
					else:
						raise Exception("{}-{}".format(response_data.status_code, response_data.text))
		else:
			raise Exception("{}-{}".format(response_data.status_code, response_data.text))

	@property
	def _return_unique_id(self):
		return ''.join([each for each in str(uuid1()).split('-')])

	# Public methods
	def connect(self) -> None:
		"""
		Connects the system with Kucoin futures account\n
		"""
		pass

	def get_account_info(self) -> dict:
		"""
		Get the account information\n
		"""
		method = "GET"
		endpoint = "/api/v1/account-overview"
		return self._request(method, endpoint)
	
	def get_asset_info(self, asset:str) -> dict:
		"""
		Get asset information\n
		Params:
			asset	:	str		= asset id. ie. XBTUSDTM
		Returns:
			Information about the asset including the precisions, base and quotes, fees
		"""
		method = "GET"
		endpoint = f"/api/v1/contracts/{asset}"
		return self._request(method, endpoint)

	def get_account_balance(self, asset:str) -> float:
		"""
		Get account free asset balance\n
		Params:
			asset	:	str		asset in the account. ie. USDT
		Returns:
			Free asset balance that can be used in trading
		"""
		method = "GET"
		endpoint = "/api/v1/account-overview"
		params = {
			"currency":asset
		}
		data = self._request(method, endpoint, params=params)
		return float(data['availableBalance'])

	def get_candle_data(self, symbol:str, timeframe:str, period:str='1d') -> pd.DataFrame:
		"""
		Get realtime candlestick data\n
		symbol		: 	str 	= symbol of the ticker\n
		timeframe	: 	str 	= timeframe of the candles\n
		period		:	str		= period of the data\n
		"""
		params = {
			'symbol':symbol,
			'granularity':int(timeframe[:-1])
		}
		data = self._request('GET','/api/v1/kline/query',params=params)
		df = pd.DataFrame(data)
		df = df.rename({0:"datetime",1:"open",2:"close",3:"high",4:"low",5:"volume"}, axis='columns')
		df.set_index('datetime', inplace=True)
		df = df[['open','high','low','close','volume']]
		df.index = df.index.astype(int)
		df['open'] = df['open'].astype(float)
		df['high'] = df['high'].astype(float)
		df['low'] = df['low'].astype(float)
		df['close'] = df['close'].astype(float)
		df['volume'] = df['volume'].astype(float)
		df.index = [datetime.fromtimestamp(x/1000,pytz.timezone(self.TIMEZONE)) for x in df.index]
		return df

	def place_order(self, symbol:str, side:str, quantity:str, order_type:str="MARKET", price:float=None, leverage:float=1, to_open:bool=True) -> str:
		"""
		Places order in connected account\n
		Params:
			symbol		:	str		=	symbol of the ticker
			side		:	str		=	side of the order. ie. buy or sell
			quantity	:	float	=	quantity of the asset to trade
			order_type	:	str		=	type of the order to execute trade. ie. MARKET, LIMIT, STOP ...
			price		:	float	=	price for the order. default None. combines with LIMIT or STOP order
			leverage	:	float	=	leverage to use for the order. default is 1.0
			to_open		:	bool	=	to open a position or close. True to open a position and False to close an open position
		
		Returns:
			order id will be returned if order executed successfully
		"""
		clOrderId = self._return_unique_id
		params = {
			'symbol':symbol,
			'side':side,
			'type':order_type.lower(),
			'size':quantity,
			'leverage':leverage,
			'clientOid':clOrderId
		}
		
		if order_type.lower() == "limit":
			params['price'] = price

		if not to_open:
			params['closeOrder'] = True
			params['reduceOnly'] = True
			del params['size']

		response = self._request('POST','/api/v1/orders',params=params)
		return response['orderId']

	def query_order(self, order_id:str) -> dict:
		"""
		Queries order\n
		Params:
			order_id	:	str		= order id to get the information of
		"""
		method = "GET"
		endpoint = f"/api/v1/orders/{order_id}"
		return self._request(method, endpoint)

	def cancel_order(self, order_id:str) -> None:
		"""
		Cancel an open order\n
		Params:
			order_id	:	str		= order id to cancel if active\n
		"""
		method = "DELETE"
		endpoint = f"/api/v1/orders/{order_id}"
		self._request(method, endpoint)

if __name__ == "__main__":

	creds = {
		"api_key":"6295b80541a5330001d17878",
		"api_secret":"03de75f3-ec16-453c-a688-73c6dee79ef2",
		"passphrase":"dummyapi",
		"account_type":"demo"
	}

	api = KucoinFuturesAPIREST(creds=creds)
	api.connect()

	# NOTE Get account info
	# account_info = api.get_account_info()
	# print(account_info)

	# NOTE Get asset balance
	# asset = "USDT"
	# asset_balance = api.get_account_balance(asset=asset)
	# print(asset_balance)

	# NOTE Get asset info
	# asset = "XBTUSDTM"
	# asset_info = api.get_asset_info(asset=asset)
	# print(asset_info)

	# NOTE Get candle data
	# symbol = "XBTUSDTM"
	# timeframe = "1m"
	# period = "1d"
	# df = api.get_candle_data(symbol=symbol, timeframe=timeframe, period=period)
	# print(df)

	# NOTE Place order
	# symbol = "XBTUSDTM"
	# side = "buy"
	# quantity = 1
	# order_type = "LIMIT"
	# price = 32500
	# leverage = 5
	# to_open = True
	# order_id = api.place_order(symbol=symbol, side=side, quantity=quantity, order_type=order_type, price=price, leverage=leverage,to_open=to_open)
	# print(order_id)

	# NOTE Query order
	# order_id = "6295b973f1ee3000016ca91e"
	# order_query = api.query_order(order_id=order_id)
	# print(order_query)

	# NOTE Cancel order
	# order_id = "6295bb46949e710001a41e67"
	# api.cancel_order(order_id=order_id)