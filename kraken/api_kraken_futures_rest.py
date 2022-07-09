# Author - Karan Parmar

"""
Kucoin FUTURES REST API
"""

# Importing built-in libraries
import json, time, pytz
from datetime import datetime
import hmac, base64, hashlib
from urllib.parse import urlencode

# Importing third-party libraries
import pandas as pd					# pip install pandas
import requests						# pip install requests

class KrakenFuturesAPIREST:

	ID = "VT_KRAKEN_FUTURES_API_REST"
	AUTHOR = "Variance Technologies"
	EXCHANGE = "Kraken"
	BROKER = "Kraken"
	MARKET = "FUTURES"

	TIMEZONE = "UTC"

	LIVE_ENDPOINT = 'https://futures.kraken.com/derivatives'
	SANDBOX_ENDPOINT = 'https://demo-futures.kraken.com/derivatives'

	nonce = 0

	def __init__(self, creds:dict):
		
		self.CREDS = creds

		if self.CREDS['account_type'].lower() in ['sandbox','testnet','test','demo']:
			self.url = self.SANDBOX_ENDPOINT
		else:
			self.url = self.LIVE_ENDPOINT

	# Private methods
	def _get_nonce(self):
		return int(1000 * time.time())

	def _sign_message(self, data:dict, urlpath:str):

		# step 1: concatenate postData, nonce + endpoint
		encoded = (urlencode(data) + str(data["nonce"])).encode()
		message =  hashlib.sha256(encoded).digest() + urlpath.encode()

		signature = hmac.new(base64.b64decode(self.CREDS['private_key']), message, hashlib.sha512)
		sigdigest = base64.b64encode(signature.digest())

		return sigdigest.decode()

	def _public_request(self, method:str, endpoint:str, params:dict="") -> dict:
		"""
		Send a public request to get publically available info\n
		"""
		return requests.request(method, self.url + endpoint, params=params).json()

	def _private_request(self, method:str, endpoint:str, data:dict={}) -> dict:
		"""
		Send a private request to interact with connected account\n
		"""
		data["nonce"] = self._get_nonce()

		sign = self._sign_message(data, endpoint)
		
		headers = {
			"APIKey":self.CREDS['public_key'],
			"Authent":sign
		}
		
		return requests.request(method, self.url + endpoint, data=data, headers=headers)

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
		endpoint = "/api/v3/accounts/"
		return self._private_request(method, endpoint).json()
	
	def get_asset_info(self, asset:str) -> dict:
		"""
		Get asset information\n
		Params:
			asset	:	str		= asset id. ie. XBTUSDTM
		Returns:
			Information about the asset including the precisions, base and quotes, fees
		"""
		method = "GET"
		endpoint = f"/api/v3/instruments"
		all_markets = self._public_request(method, endpoint)['instruments']

		for market in all_markets:
			if market['type'] == "flexible_futures":
				if market['symbol'] == 'pf_' + asset.lower().replace('_','').replace('-',''):
					return market

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

		if to_open:
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
		"public_key":"glT+JjLLKuo6Z6hhtW7f/v9SgWMx3sRTitumeo4hlGVXzC03lMjVqe/q",
		"private_key":"VJZIMIlc5g/gGNFIFuAT01+jVpvJvJNHeOsngBeed+mVYUUdqcYz8See51QrdNZXHegMGxQLkXzskz30fAW6oZwf",
		"account_type":"demo"
	}

	api = KrakenFuturesAPIREST(creds=creds)
	api.connect()

	# NOTE Get account info
	account_info = api.get_account_info()
	print(account_info)

	# NOTE Get asset balance
	# asset = "USDT"
	# asset_balance = api.get_account_balance(asset=asset)
	# print(asset_balance)

	# NOTE Get asset info
	# asset = "XBTUSD"
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