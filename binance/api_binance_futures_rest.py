# Author - Karan Parmar

"""
Binance FUTURES API REST
"""

# Importing built-in libraries
import pytz							# pip install pytz
from datetime import datetime

# Importing third-party libraries
import pandas as pd					# pip install pandas
from binance.client import Client	# pip install python-binance

class BinanceFuturesAPIREST:

	ID = "VT_BINANCE_FUTURES_API_REST"
	AUTHOR = "Variance Technologies"
	EXCHANGE = "BINANCE"
	BROKER = "BINANCE"
	MARKET = "FUTURES"

	def __init__(self, creds:dict):

		self.CREDS = creds

	# Public methods
	def connect(self) -> None:
		"""
		Connects to Binance Futures account\n
		"""
		self.client = Client(
			api_key=self.CREDS['api_key'],
			api_secret=self.CREDS['api_secret'],
			testnet=self.CREDS['account_type'].lower() in ['testnet','sandbox','test','demo'],
		)

	def get_account_info(self) -> dict:
		"""
		Get connected account info\n
		"""
		return self.client.futures_account()

	def get_asset_info(self, asset:str) -> dict:
		"""
		Get asset information\n
		"""
		symbols = self.client.futures_exchange_info()['symbols']
		for i in symbols:
			if i['symbol'] == asset.upper():
				return i

	def get_account_balance(self, asset:str="USDT") -> float:
		"""
		Get connected aaccount's free asset balance\n
		"""
		for i in self.client.futures_account_balance():
			if i['asset'] == asset.upper():
				return float(i['withdrawAvailable'])
		
	def get_candle_data(self, symbol:str, timeframe:str, period:str='1d') -> pd.DataFrame:
		"""
		Returns historcal klines from past for given symbol and interval\n
		"""
		if period[-1] == 'd':
			pastDays = int(period[:-1])
		start_str=str((pd.to_datetime('today')-pd.Timedelta(str(pastDays)+' days')).date())
		df = pd.DataFrame(self.client.futures_klines(symbol=symbol,start_str=start_str,interval=timeframe))
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

	def place_order(self, symbol:str, side:str, quantity:float, order_type:str="MARKET", price:float=None, to_open:bool=True) -> str:
		"""
		Places order in connected account\n
		Params:
			symbol		:	str		=	symbol of the ticker
			side		:	str		=	side of the order. ie. buy or sell
			quantity	:	float	=	quantity of the asset to trade
			order_type	:	str		=	type of the order to execute trade. ie. MARKET, LIMIT, STOP ...
			price		:	float	=	price for the order. default None. combines with LIMIT or STOP order
			to_open		:	bool	=	to open a position or close. True means open a position, False to close an open position
		
		Returns:
			order id will be returned if order executed successfully
		"""
		# Setting hedge mode to open and close positions
		positionMode = self.client.futures_get_position_mode()['dualSidePosition']
		(not positionMode) and self.client.futures_change_position_mode(dualSidePosition=True)
		
		# NOTE Placing entry order
		body = {
			"symbol":symbol,
			"side":side.upper(),
			"positionSide":"LONG" if side.lower() == 'buy' else "SHORT",
			"quantity":quantity,
			"type":order_type.upper()
		}

		if order_type.lower() == "limit":
			body['price'] = price
			body['timeInForce'] = "GTC"

		if not to_open:
			body['positionSide'] = "LONG" if side.lower() == 'sell' else "SHORT"
			body['closePosition'] = True
			body['reduceOnly'] = True
			del body['quantity']

		return self.client.futures_create_order(**body)['orderId']

	def set_leverage(self, symbol:str, leverage:int) -> None:
		"""
		Sets leverage\n
		Params:
			symbol		:	str		=	Symbol of the ticker
			leverage	: 	int		=	Leverage to set
		"""
		self.client.futures_change_leverage(symbol=symbol, leverage=leverage)

	def cancel_order(self, symbol:str, order_id:int) -> None:
		"""
		Cancel the order\n
		Params:
			symbol		:	str		=	order ticker symbol
			order_id	:	str		=	order id to cancel
		"""
		self.client.futures_cancel_order(symbol=symbol, orderId=order_id)

	def query_order(self, symbol:str, order_id:str) -> dict:
		"""
		Query order\n
		Params:
			symbol		:	str		=	order ticker symbol
			order_id	:	str		=	order id to query
		"""
		return self.client.futures_get_order(symbol=symbol, orderId=order_id)

if __name__ == "__main__":

	creds = {
		"api_key":"881c6d67c787bda4be358e9a00ee2e3d6ef4ca9795597c0f47e1f98eaccb4373",
		"api_secret":"1c993b53a0ce050c69c3f3311d1d431ba13fc9f05db907ded4d88132608113c7",
		"account_type":"testnet"
	}

	api = BinanceFuturesAPIREST(creds=creds)
	api.connect()

	# NOTE Get account 
	# accountInfo = api.get_account()
	# print(accountInfo)

	# NOTE Get account balance
	# asset = "USDT"
	# balance = api.get_account_balance(asset=asset)
	# print(balance)

	# NOTE Get asset info
	# asset = "BTCUSDT"
	# assetInfo = api.get_asset_info(asset=asset)
	# print(assetInfo)

	# NOTE Get candle data
	# symbol = 'BTCUSDT'
	# timeframe = '1m'
	# df = api.get_candle_data(symbol=symbol, timeframe=timeframe)
	# print(df)

	# NOTE Place order
	# symbol = "BTCUSDT"
	# side = "buy"
	# quantity = 0.001
	# orderType = "MARKET"
	# price = None,
	# stoploss = 29010
	# targetprofit = 29080
	# entryId, slId, tpId = api.place_order(
	# 		symbol=symbol, 
	# 		side=side, 
	# 		quantity=quantity, 
	# 		orderType=orderType, 
	# 		price=price,
	# 		stoploss=stoploss,
	# 		targetprofit=targetprofit
	# 	)
	# print(entryId, slId, tpId)

	# NOTE Cancel order
	# symbol = "BTCUSDT"
	# orderId = 3041027512
	# api.cancel_order(symbol=symbol, orderId=orderId)

	# NOTE Query order
	# 3041027511 3041027512 3041027514
	# symbol = "BTCUSDT"
	# orderId = 3041027511
	# query = api.query_order(symbol=symbol, orderId=orderId)['status']
	# print(query)