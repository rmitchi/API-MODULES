# Author - Karan Parmar

"""
BINANCE SPOT REST API
"""

# Importing built-in libraries
import pytz 						# pip install pytz
from datetime import datetime

# Importing thid-party libraries
import pandas as pd					# pip install pandas
from binance.client import Client	# pip install python-binance

class BinanceSPOTAPIREST:

	ID = "VT_API_REST_BINANCE_SPOT"
	NAME = "Binance SPOT REST API"
	AUTHOR = "Variance Technologies pvt. ltd."
	EXCHANGE = "BINANCE"
	BROKER = "BINANCE"
	MARKET = "SPOT"

	def __init__(self,creds:dict):
		
		self.CREDS = creds

	# Public methods
	def connect(self) -> None:
		"""
		Connects to binance SPOT account\n
		"""
		self.client = Client(
				api_key=self.CREDS['api_key'],
				api_secret=self.CREDS['api_secret'],
				testnet=True if self.CREDS['account_type'].lower() in ['testnet','sandbox','demo','test'] else False
			)

	def get_account_info(self) -> dict:
		"""
		Returns account information\n
		"""
		return self.client.get_account()

	def get_account_balance(self, asset:str='USDT') -> float:
		"""
		Returns free asset balance for given asset\n
		"""
		return float(self.client.get_asset_balance(asset=asset)['free'])

	def get_asset_info(self, asset:str) -> dict:
		"""
		Returns asset information\n
		Params:
			asset	:	str		= Asset to get information of. ie. BTCUSDT
		Returns:

		"""
		symbols =  self.client.get_exchange_info()['symbols']
		for i in symbols:
			if i['symbol'] == asset.upper():
				return i

	def get_candle_data(self, symbol:str, timeframe:str, period:str='1d') -> pd.DataFrame:
		"""
		Returns historcal klines from past for given symbol and interval\n
		"""
		if period[-1] == 'd':
			pastDays = int(period[:-1])
		start_str=str((pd.to_datetime('today')-pd.Timedelta(str(pastDays)+' days')).date())
		df = pd.DataFrame(Client().get_historical_klines(symbol=symbol,start_str=start_str,interval=timeframe))
		df.columns = ['open_time','open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol','is_best_match']
		df.index = [datetime.fromtimestamp(x/1000, tz=pytz.timezone('UTC')) for x in df.open_time]
		df = df[['open', 'high', 'low', 'close', 'volume']]
		
		df['open'] = df['open'].astype(float)
		df['high'] = df['high'].astype(float)
		df['low'] = df['low'].astype(float)
		df['close'] = df['close'].astype(float)
		df['volume'] = df['volume'].astype(float)
		
		df.index.name = 'datetime'
		return df
	
	def place_order(self, symbol:str, side:str, quantity:float, order_type:str="MARKET", price:float=None) -> int:
		"""
		Places order in Binance SPOT account\n
		"""
		body = {
			"symbol":symbol.upper(),
			"side":side.upper(),
			"type":order_type.upper(),
			"quantity":quantity,
		}
		if order_type.upper() == 'LIMIT':
			body['timeInForce'] = "GTC"
			body['price'] = price
		return self.client.create_order(**body)['orderId']

	def query_order(self, symbol:str, order_id:str) -> dict:
		"""
		Get order information\n
		"""
		return self.client.get_order(symbol=symbol, orderId=order_id)

	def cancel_order(self, symbol:str, order_id:str) -> None:
		"""
		Cancel open order\n
		"""
		try:
			self.client.cancel_order(symbol=symbol, orderId=order_id)
		except Exception:
			pass

if __name__ == "__main__":

	creds = {
		"api_key":"fa9jqiAMACRIt4eNiWGeDBPRc7DP2hrbYmVwNh8EN9qgJfuP2AfOwy1jyCBoyda3",
		"api_secret":"XJn71It6IBfIqonToPK7GrxNCfjuyWeWqUccmJOXGDO9h7NWJONBQpkbfcc66oV3",
		"account_type":"testnet"
	}

	api = BinanceSPOTAPIREST(creds)
	api.connect()

	# NOTE Get account info
	# account_info = api.get_account_info()
	# print(account_info)

	# NOTE Get asset balance
	# asset = 'USDT'
	# asset_balance = api.get_account_balance(asset=asset)
	# print(asset_balance)

	# NOTE Get asset info
	# asset = "BTCUSDT"
	# asset_info = api.get_asset_info(asset=asset)
	# print(asset_info)

	# NOTE Get candle data
	# symbol = 'BTCUSDT'
	# timeframe = '1m'
	# df = api.get_candle_data(symbol=symbol, timeframe=timeframe, period='1d')
	# print(df)

	# NOTE Place order
	# symbol = "BTCUSDT"
	# side = "buy"
	# quantity = 0.001
	# order_type = "LIMIT"
	# price = 21100
	# order_id = api.place_order(
	# 	symbol=symbol,
	# 	side=side,
	# 	quantity=quantity,
	# 	order_type=order_type,
	# 	price=price,
	# )
	# print(order_id)

	# NOTE Query order
	# symbol = "BTCUSDT"
	# order_id = 2588185
	# order_query = api.query_order(symbol=symbol, order_id=order_id)
	# print(order_query)

	# NOTE Cancel order
	# symbol = "BTCUSDT"
	# order_id = 2588185
	# api.cancel_order(symbol=symbol, order_id=order_id)