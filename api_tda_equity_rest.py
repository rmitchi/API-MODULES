# Author - Karan Parmar

"""
TD AMERITRADE EQUITY REST API
"""

# Importing built-in libraries
import pytz								# pip install pytz
from datetime import datetime

# Importing third-party libraries
import requests
import pandas as pd						# pip install pandas
import tda								# pip install tda-api
from tda import auth
from tda.utils import Utils
from tda.orders.generic import OrderBuilder
from tda.orders.common import EquityInstruction, OrderStrategyType, OrderType, Session, Duration, StopPriceLinkType, StopPriceLinkBasis

class TDAEquityRESTAPI:

	ID = "VT_TDA_EQUITY_API_REST"
	AUTHOR = "Variance Technologies"
	EXCHANGE = "SMART"
	BROKER = "TDA"
	MARKET = "EQUITY"

	def __init__(self, creds:dict):

		self.CREDS = creds

		self.API_KEY = creds['api_key']
		self.TOKEN_PATH = "tda_access_token.json"

		self.TIMEZONE = "US/Eastern"

	# Helper methods
	@staticmethod
	def _configure_api_key(key:str):
		"""
		Configure API key and assign to bot\n
		"""
		if '@AMER.OAUTHAP' in key.upper():
			return key
		else:
			return key + '@AMER.OAUTHAP'

	# Public methdos
	def connect(self) -> None:
		"""
		Connect to TD Ameritrade account\n
		"""
		try:
			self.client = auth.client_from_token_file(token_path=self.TOKEN_PATH, api_key=self.API_KEY)
		except FileNotFoundError:
			raise Exception('\nToken not found, Generate a token first\n')

	def get_candle_data(self, symbol:str, timeframe:str, period='1d'):
		"""
		Get realtime candlestick data\n
		symbol		: str 	= symbol of the ticker\n
		timeframe	: str 	= timeframe of the candles\n
		"""
		url = f"https://api.tdameritrade.com/v1/marketdata/{symbol}/pricehistory"

		_freq = {
			'm':'minute',
			'd':'day',
			'w':'weekly',
			'M':'monthly'
		}
		_period = {
			'':None,
			'd':'day',
			'M':'month',
			'y':'year',
			'Y':'year',
			'ytd':'ytd'
		}
		params = {}
		params.update({'apikey': self.API_KEY})
		params['needExtendedHoursData'] = False
		kwargs = {
			'period':period[:-1],
			'periodType':_period[period[-1]],
			'frequencyType':_freq[timeframe[-1]],
			'frequency':int(timeframe[:-1]),
		}

		for arg in kwargs:
			parameter = {arg: kwargs.get(arg)}
			params.update(parameter)
		
		response = requests.get(url, params=params).json()
		df = pd.DataFrame(response['candles'])
		df.index = [datetime.fromtimestamp(x/1000, tz=pytz.timezone(self.TIMEZONE)) for x in df.datetime]
		df = df[['open','high','low','close','volume']]
		return df

	def place_order(self, symbol:str, side:str, quantity:int, orderType:str="MARKET", price:float=None) -> int:
		"""
		Places order in connected account\n
		symbol		: str	= symbol of the ticker\n
		side		: str	= side of the order. ie. buy, sell\n
		quantity	: int 	= no of shares to execute as quantity\n
		orderType	: str	= order type. ie. MARKET, LIMIT, STOP...\n
		price		: float	= price to place limit or stop\n
		"""
		orderType = orderType.upper()

		if side.lower() == 'buy':
			
			if orderType == 'MARKET':
				order = tda.orders.equities.equity_buy_market(symbol,quantity)
			
			elif orderType == 'LIMIT':
				order = tda.orders.equities.equity_buy_limit(symbol,quantity,price)
				
			
		elif side.lower() == 'sell':
			
			if orderType == 'MARKET':
				order = tda.orders.equities.equity_sell_market(symbol,quantity)
			
			elif orderType == 'LIMIT':
				order = tda.orders.equities.equity_sell_limit(symbol,quantity,price)
			
		response = self.client.place_order(self.ACCOUNT_ID,order)
		return Utils(self.client,self.ACCOUNT_ID).extract_order_id(place_order_response=response)

	def place_trailing_stop(self, symbol:str, side:str, quantity:int, trailOffset:float=10) -> int:
		"""
		Places trailing stoploss order\n
		symbol		: str	= symbol of the ticker\n
		side		: str	= side of the order. ie. buy, sell\n
		quantity	: int 	= no of shares to execute as quantity\n
		trailOffset	: float	= trailing stoploss offset\n
		"""
		order = (OrderBuilder()
					.set_order_type(OrderType.TRAILING_STOP)
					.set_session(Session.NORMAL)
					.set_duration(Duration.DAY)
					.set_stop_price_link_type(StopPriceLinkType.PERCENT)
					.set_stop_price_link_basis(StopPriceLinkBasis.LAST)
					.set_order_strategy_type(OrderStrategyType.SINGLE)
					.set_order_type(OrderType.TRAILING_STOP)
					.set_stop_price_offset(trailOffset)
				)
		if side == 'buy':
			order.add_equity_leg(EquityInstruction.BUY, symbol, quantity)
		elif side == 'sell':
			order.add_equity_leg(EquityInstruction.SELL, symbol, quantity)

		response = self.client.place_order(self.ACCOUNT_ID,order)
		return Utils(self.client,self.ACCOUNT_ID).extract_order_id(place_order_response=response)

	def query_order(self, orderId:int):
		"""
		Queries order status by orderId\n
		"""
		return self.client.get_order(orderId,self.ACCOUNT_ID).json()['status']

	def cancel_order(self,orderId:int):
		"""
		Cancels order by orderId\n
		"""
		self.client.cancel_order(orderId,self.ACCOUNT_ID)


if __name__ == "__main__":

	creds = {
		"api_key":"KORNTRADING",
		"account_id":"",
		"redirect_uri":""
	}

	api = TDAEquityRESTAPI(creds)
	# api.connect()

	# Get candle data
	symbol = "AAPL"
	timeframe = "1m"
	period = "1d"
	df = api.get_candle_data(symbol=symbol, timeframe=timeframe, period=period)
	print(df)