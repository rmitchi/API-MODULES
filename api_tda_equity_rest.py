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
import undetected_chromedriver as uc	# pip install undetected_chromedriver
import tda								# pip install tda-api
from tda import auth
from tda.utils import Utils
from tda.orders.generic import OrderBuilder
from tda.orders.common import EquityInstruction, OrderStrategyType, OrderType, Session, Duration, StopPriceLinkType, StopPriceLinkBasis

class TDAEquityRESTAPI:

	ID = "VT_API_REST_TDA_EQUITY"
	AUTHOR = "Variance Technologies pvt. ltd."
	EXCHANGE = "SMART"
	BROKER = "TDA"
	MARKET = "EQUITY"

	TIMEZONE = "US/Eastern"

	TOKEN_PATH = "tda_access_token.json"

	_chrome_driver_version = 102

	def __init__(self, creds:dict):

		self.CREDS = creds

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
			self.client = auth.client_from_token_file(token_path=self.TOKEN_PATH, api_key=self.CREDS['api_key'])
		except FileNotFoundError:
			driver = uc.Chrome(version_main=self._chrome_driver_version)
			self.client = auth.client_from_login_flow(driver, self.CREDS['creds'], self.CREDS['redirect_uri'], self.TOKEN_PATH)

	def get_account_info(self) -> dict:
		"""
		Get connected account information\n
		"""
		return self.client.get_account(account_id=self.CREDS['account_id'])

	def get_account_balance(self) -> float:
		"""
		Get free USD account balance\n
		"""
		return

	def get_candle_data(self, symbol:str, timeframe:str, period='1d') -> pd.DataFrame:
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
		params.update({'apikey': self.CREDS['api_key']})
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
		return df[['open','high','low','close','volume']]

	def place_order(self, symbol:str, side:str, quantity:int, order_type:str="MARKET", price:float=None, to_open:bool=True) -> int:
		"""
		Places order in connected account\n
		symbol		: 	str		= symbol of the ticker\n
		side		: 	str		= side of the order. ie. buy, sell\n
		quantity	: 	int 	= no of shares to execute as quantity\n
		order_type	: 	str		= order type. ie. MARKET, LIMIT, STOP...\n
		price		: 	float	= price to place limit or stop\n
		to_open		: 	bool	=	to open a position or close
		"""
		order_type = order_type.upper()

		if side.lower() == 'buy':
			
			if order_type == 'MARKET':
				if to_open:
					order = tda.orders.equities.equity_buy_market(symbol, quantity)
				else:
					order = tda.orders.equities.equity_buy_to_cover_market(symbol, quantity)
			
			elif order_type == 'LIMIT':
				if to_open:
					order = tda.orders.equities.equity_buy_limit(symbol, quantity, price)
				else:
					order = tda.orders.equities.equity_buy_to_cover_limit(symbol, quantity, price)
				
		elif side.lower() == 'sell':
			
			if order_type == 'MARKET':
				if to_open:
					order = tda.orders.equities.equity_sell_short_market(symbol, quantity)
				else:
					order = tda.orders.equities.equity_sell_market(symbol, quantity)
			
			elif order_type == 'LIMIT':
				if to_open:
					order = tda.orders.equities.equity_sell_short_limit(symbol, quantity, price)
				else:
					order = tda.orders.equities.equity_sell_limit(symbol, quantity, price)
			
		response = self.client.place_order(self.CREDS['account_id'], order)
		return Utils(self.client,self.CREDS['account_id']).extract_order_id(place_order_response=response)

	def place_trailing_stop(self, symbol:str, side:str, quantity:int, trail_offset:float=10) -> int:
		"""
		Places trailing stoploss order\n
		symbol		: str	= symbol of the ticker\n
		side		: str	= side of the order. ie. buy, sell\n
		quantity	: int 	= no of shares to execute as quantity\n
		trail_offset	: float	= trailing stoploss offset\n
		"""
		order = (OrderBuilder()
					.set_order_type(OrderType.TRAILING_STOP)
					.set_session(Session.NORMAL)
					.set_duration(Duration.DAY)
					.set_stop_price_link_type(StopPriceLinkType.PERCENT)
					.set_stop_price_link_basis(StopPriceLinkBasis.LAST)
					.set_order_strategy_type(OrderStrategyType.SINGLE)
					.set_order_type(OrderType.TRAILING_STOP)
					.set_stop_price_offset(trail_offset)
				)
		if side == 'buy':
			order.add_equity_leg(EquityInstruction.BUY, symbol, quantity)
		elif side == 'sell':
			order.add_equity_leg(EquityInstruction.SELL, symbol, quantity)

		response = self.client.place_order(self.CREDS['account_id'], order)
		return Utils(self.client,self.CREDS['account_id']).extract_order_id(place_order_response=response)

	def query_order(self, order_id:int):
		"""
		Queries order info by order_id\n
		"""
		return self.client.get_order(order_id, self.CREDS['account_id']).json()

	def cancel_order(self, order_id:int):
		"""
		Cancels open order by order_id\n
		"""
		try:
			self.client.cancel_order(order_id, self.CREDS['account_id'])
		except Exception:
			pass


if __name__ == "__main__":

	creds = {
		"account_id":"",
		"api_key":"",
		"redirect_uri":""
	}

	api = TDAEquityRESTAPI(creds)
	api.connect()

	# NOTE Get account info
	# account_info = api.get_account_info()
	# print(account_info)

	# NOTE Get account balance
	# account_balance = api.get_account_balance()
	# print(account_balance)

	# NOTE Get candle data
	# symbol = "AAPL"
	# timeframe = "1m"
	# period = "1d"
	# df = api.get_candle_data(symbol=symbol, timeframe=timeframe, period=period)
	# print(df)

	# NOTE Place order
	# symbol = "MRNA"
	# side = "buy"
	# quantity = 1
	# order_type = "MARKET"
	# price = None
	# to_open = True
	# order_id = api.place_order(
	# 	symbol=symbol,
	# 	side=side,
	# 	quantity=quantity,
	# 	order_type=order_type,
	# 	price=price,
	# 	to_open=to_open,
	# )

	# NOTE Query order
	# order_id = 123456
	# order_info = api.query_order(order_id=order_id)
	# print(order_info)

	# NOTE Cancel order
	# order_id = 123456
	# api.cancel_order(order_id=order_id)