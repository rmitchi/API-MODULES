# Author - Karan Parmar

"""
FTX FUTURES API REST
"""

# Importing built-in libraries
import time
import pytz							# pip install pytz
from datetime import datetime, timedelta
import hmac, urllib

# Importing third-party libraries
import pandas as pd					# pip install pandas
from requests import Request, Response, Session

class FTXFuturesAPIREST:

	ID = "VT_FTX_FUTURES_API_REST"
	AUTHOR = "Variance Technologies"
	EXCHANGE = "FTX"
	BROKER = "FTX"
	MARKET = "FUTURES"

	LIVE_ENDPOINT = "https://ftx.com/api"

	def __init__(self, creds:dict):

		self.CREDS = creds

		self._client = Session()

		self.url = self.LIVE_ENDPOINT

	# Private methods
	def _request(self, method: str, path: str, params:dict={}) -> dict:
		if method == "GET":
			request = Request(method, self.url + path, params=params)
		elif method == "POST":
			request = Request(method, self.url + path, json=params)
	
		self._sign_request(request)
		response = self._client.send(request.prepare())
		return self._process_response(response)

	def _sign_request(self, request:Request) -> None:
		ts = int(time.time() * 1000)
		prepared = request.prepare()
		signature_payload = f'{ts}{prepared.method}{prepared.path_url}'.encode()
		if prepared.body:
			signature_payload += prepared.body
		signature = hmac.new(self.CREDS['api_secret'].encode(), signature_payload, 'sha256').hexdigest()
		request.headers['FTX-KEY'] = self.CREDS['api_key']
		request.headers['FTX-SIGN'] = signature
		request.headers['FTX-TS'] = str(ts)
		if self.CREDS.get('subaccount_name'):
			request.headers['FTX-SUBACCOUNT'] = urllib.parse.quote(self.CREDS['subaccount_name'])

	def _process_response(self, response: Response) -> dict:
		try:
			data = response.json()
		except ValueError:
			response.raise_for_status()
			raise
		else:
			if not data['success']:
				raise Exception(data['error'])
			return data['result']

	# Public methods
	def connect(self) -> None:
		"""
		Connects to Binance Futures account\n
		"""
		pass

	def get_account_info(self) -> dict:
		"""
		Get connected account info\n
		"""
		method = "GET"
		endpoint = "/account"
		return self._request(method, endpoint)

	def get_asset_info(self, asset:str) -> dict:
		"""
		Get asset information\n
		"""
		method = "GET"
		endpoint = f"/markets/{asset}"
		return self._request(method, endpoint)

	def get_account_balance(self, asset:str="USDT") -> float:
		"""
		Get connected aaccount's free asset balance\n
		"""
		method = "GET"
		endpoint = "/wallet/balances"
		return float(self._request(method, endpoint)[-1]['availableForWithdrawal'])

	def get_candle_data(self, symbol:str, timeframe:str, period:str='1d') -> pd.DataFrame:
		"""
		Returns historcal klines from past for given symbol and interval\n
		"""
		_frame_multiplier = {
			'm':60,
			'h':3600,
			'd':86400
		}
		ct = datetime.now()
		s = int((ct - timedelta(days=int(period[:-1]))).timestamp())
		e = int(ct.timestamp())

		method = "GET"
		endpoint = f"/markets/{symbol}/candles"

		params = {
			"resolution":int(timeframe[:-1]) * _frame_multiplier[timeframe[-1]],
			"start_time":s,
			"end_time":e,
		}
		data = self._request(method, endpoint, params)
		df = pd.DataFrame(data)
		df.index = pd.DatetimeIndex(df.startTime)
		return df[['open','high','low','close','volume']]

	def place_order(self, symbol:str, side:str, quantity:float, order_type:str="MARKET", price:float=None, to_open:bool=True) -> str:
		"""
		Places order in connected account\n
		Params:
			symbol		:	str		=	symbol of the ticker
			side		:	str		=	side of the order. ie. buy or sell
			quantity	:	float	=	quantity of the asset to trade
			order_type	:	str		=	type of the order to execute trade. ie. MARKET, LIMIT, STOP ...
			price		:	float	=	price for the order. default None. combines with LIMIT or STOP order
			to_open		:	bool	= 	to open a position
		
		Returns:
			order id will be returned if order executed successfully
		"""
		method = "POST"
		endpoint = "/orders"

		params = {
			"market":symbol,
			"side":side.lower(),
			"type":order_type.lower(),
			"size":quantity,
			"price":None
		}
		if not to_open:
			params['reduceOnly'] = True
			del params['side']
		
		if order_type.lower() == "limit":
			params['price'] = price

		return self._request(method, endpoint, params)['id']

	def set_leverage(self, symbol:str, leverage:int) -> None:
		"""
		Sets leverage\n
		"""
		pass

	def cancel_order(self, order_id:int) -> None:
		"""
		Cancel the order\n
		"""
		method = "DELETE"
		endpoint = f"/orders/{order_id}"
		self._request(method, endpoint)

	def query_order(self, order_id:str) -> dict:
		"""
		Query order\n
		"""
		method = "GET"
		endpoint = f"/orders/{order_id}"
		return self._request(method, endpoint)

if __name__ == "__main__":

	creds = {
		"api_key":"MGgz-ClgXL6qVklvJzeg5e_ZmsySVQsroKS99v6o",
		"api_secret":"SieG4qsh6IEzxa4-jWUTJXxcbHZHb3Qv0Q920wys",
		"account_type":"live"
	}

	api = FTXFuturesAPIREST(creds=creds)
	api.connect()

	# NOTE Get account 
	# account_info = api.get_account_info()
	# print(account_info)

	# NOTE Get account balance
	# asset = "USDT"
	# balance = api.get_account_balance(asset=asset)
	# print(balance)

	# NOTE Get asset info
	# asset = "BTC-PERP"
	# asset_info = api.get_asset_info(asset=asset)
	# print(asset_info)

	# NOTE Get candle data
	# symbol = 'BTC-PERP'
	# timeframe = '1m'
	# df = api.get_candle_data(symbol=symbol, timeframe=timeframe)
	# print(df)

	# NOTE Place order
	symbol = "XRP-PERP"
	side = "buy"
	quantity = 1
	order_type = "MARKET"
	price = None
	order_id= api.place_order(
			symbol=symbol, 
			side=side, 
			quantity=quantity, 
			order_type=order_type, 
			price=price,
			to_open=True
		)
	print(order_id)

	# NOTE Cancel order
	# symbol = "BTCUSDT"
	# order_id = 3041027512
	# api.cancel_order(symbol=symbol, order_id=order_id)

	# NOTE Query order
	# 3041027511 3041027512 3041027514
	# symbol = "BTCUSDT"
	# order_id = 3041027511
	# query = api.query_order(symbol=symbol, order_id=order_id)['status']
	# print(query)