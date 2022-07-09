# Author - Karan Parmar

"""
TD AMERITRADE OPTIONS REST API
"""

# Importing built-in libraries
import pytz								# pip install pytz
import datetime as dt
from datetime import datetime, timedelta

# Importing third-party libraries
import requests
import pandas as pd						# pip install pandas
import undetected_chromedriver as uc	# pip install undetected_chromedriver
import tda								# pip install tda-api
from tda import auth
from tda.utils import Utils
from tda.orders.generic import OrderBuilder
from tda.orders.common import OptionInstruction, OrderStrategyType, OrderType, Session, Duration, StopPriceLinkType, StopPriceLinkBasis

class TDAOptionsRESTAPI:

	ID = "VT_API_REST_TDA_OPTIONS"
	AUTHOR = "Variance Technologies pvt. ltd."
	EXCHANGE = "SMART"
	BROKER = "TDA"
	MARKET = "OPTIONS"

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

	@staticmethod
	def get_tda_options_symbol(symbol:str, expiry:dt.date, strike_price:int, call_put:str) -> str:
		"""
		Returns tda options symbol\n
		"""
		expiry = f"{int(expiry.month):02d}{int(expiry.day):02d}{str(expiry.year)[-2:]}"
		call_put = call_put[0].upper()
		return f"{symbol}_{expiry}{call_put}{int(strike_price)}"

	# Public methdos
	def connect(self) -> None:
		"""
		Connect to TD Ameritrade account\n
		"""
		try:
			self.client = auth.client_from_token_file(token_path=self.TOKEN_PATH, api_key=self.CREDS['api_key'])
		except FileNotFoundError:
			driver = uc.Chrome(version_main=self._chrome_driver_version)
			self.client = auth.client_from_login_flow(driver, self.CREDS['api_key'], self.CREDS['redirect_uri'], self.TOKEN_PATH)

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

	def get_options_chain(self, symbol:str, expiry:int=0):
		"""
		Downloading option chain data from TDA API\n
		"""
		url = f"https://api.tdameritrade.com/v1/marketdata/chains"
		
		params = {}
		params.update({'apikey': self.API_KEY})
		params['symbol'] = symbol
		params['toDate'] = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")

		response = requests.get(url, params=params).json()
		# print(response)

		call_expiries_map = response['callExpDateMap']
		put_expiries_map = response['putExpDateMap']

		_dates = [datetime.strptime(i[:10],"%Y-%m-%d").date() for i in call_expiries_map]
		expiry_dates = [i for i in call_expiries_map]
		# print(expiry_dates)

		_maps = {
			'call':call_expiries_map,
			'put':put_expiries_map,
		}
		if expiry is not None:
			expiries = [expiry]
		else:
			expiries = list(range(len(expiry_dates)))
		
		chain = {}
		for expiry in expiries:
			x = expiry_dates[expiry][:10]
			chain[x] = {}
			for strike_price in call_expiries_map[expiry_dates[expiry]]:
				chain[x][strike_price] = {}
				for cp, _map in _maps.items():
					chain[x][strike_price][cp] = {
						'symbol':_map[expiry_dates[expiry]][strike_price][0]['symbol'],
						'ask':_map[expiry_dates[expiry]][strike_price][0]['ask'],
						'bid':_map[expiry_dates[expiry]][strike_price][0]['bid'],
						'ltp':_map[expiry_dates[expiry]][strike_price][0]['closePrice'],
					}

		return chain

	def place_order(
			self, 
			symbol:str,
			expiry:dt.date,
			strike_price:int,
			call_put:str,
			side:str, 
			quantity:int, 
			order_type:str="MARKET", 
			price:float=None, 
			to_open:bool=True,
		) -> int:
		"""
		Places order in connected account\n
		symbol		: str		= symbol of the ticker\n
		expiry 		: dt.date	= expiry date\n
		strike_price: int		= strike price of the asset\n
		call_put	: str		= call or put\n
		side		: str		= side of the order. ie. buy, sell\n
		quantity	: int 		= no of shares to execute as quantity\n
		order_type	: str		= order type. ie. MARKET, LIMIT, STOP...\n
		price		: float		= price to place limit or stop\n
		to_open		: bool		= To open or close the option positions\n
		"""
		symbol = self.get_tda_options_symbol(symbol=symbol, expiry=expiry, strike_price=strike_price, call_put=call_put)
		order_type = order_type.upper()

		if side.lower() == 'buy':
			
			if order_type == 'MARKET':
				if to_open:
					order = tda.orders.options.option_buy_to_open_market(symbol,quantity)
				else:
					order = tda.orders.options.option_buy_to_close_market(symbol,quantity)

			elif order_type == 'LIMIT':
				if to_open:
					order = tda.orders.options.option_buy_to_open_limit(symbol,quantity,price)
				else:
					order = tda.orders.options.option_buy_to_close_limit(symbol,quantity,price)
			
		elif side.lower() == 'sell':
			
			if order_type == 'MARKET':
				if to_open:
					order = tda.orders.options.option_sell_to_open_market(symbol,quantity)
				else:
					order = tda.orders.options.option_sell_to_close_market(symbol, quantity)

			elif order_type == 'LIMIT':
				if to_open:
					order = tda.orders.options.option_sell_to_open_limit(symbol,quantity,price)
				else:
					order = tda.orders.options.option_sell_to_close_limit(symbol, quantity, price)

		response = self.client.place_order(self.CREDS['account_id'], order)
		return Utils(self.client, self.CREDS['account_id']).extract_order_id(place_order_response=response)

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
		if side.lower() == 'buy':
			order.add_equity_leg(OptionInstruction.BUY_TO_CLOSE, symbol, quantity)
		elif side.lower() == 'sell':
			order.add_equity_leg(OptionInstruction.SELL_TO_CLOSE, symbol, quantity)

		response = self.client.place_order(self.CREDS['account_id'], order)
		return Utils(self.client, self.CREDS['account_id']).extract_order_id(place_order_response=response)

	def place_vertical_spread_order(self, long_strike_symbol:str, short_strike_symbol:str, call_put:str, quantity:int, net_credit:float) -> int:
		"""
		Places vertical spread order\n
		"""
		if call_put == 'call':
			order = tda.orders.options.bear_call_vertical_open(
				long_call_symbol=long_strike_symbol,
				short_call_symbol=short_strike_symbol,
				quantity=quantity,
				net_credit=net_credit
			)
		
		elif call_put == 'put':
			order = tda.orders.options.bull_put_vertical_open(
				long_call_symbol=long_strike_symbol,
				short_call_symbol=short_strike_symbol,
				quantity=quantity,
				net_credit=net_credit
			)
		
		response = self.client.place_order(self.CREDS['account_id'], order)
		return Utils(self.client, self.CREDS['account_id']).extract_order_id(place_order_response=response)

	def query_order(self, order_id:int):
		"""
		Queries order status by order_id\n
		"""
		return self.client.get_order(order_id, self.CREDS['account_id']).json()

	def cancel_order(self,order_id:int):
		"""
		Cancels order by order_id\n
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

	api = TDAOptionsRESTAPI(creds)
	# api.connect()

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

	# NOTE Get option-chain
	# symbol = "SPY"
	# chain = api.get_options_chain(symbol=symbol)
	# print(chain)

	# NOTE Get TDA options symbol
	# symbol = "SPY"
	# expiry = dt.date(2022, 6, 24)
	# strike_price = 452
	# call_put = "call"
	# options_symbol = api.get_tda_options_symbol(symbol=symbol, expiry=expiry, strike_price=strike_price, call_put=call_put)
	# print(options_symbol)

	# NOTE Place order
	# symbol = "SPY"
	# expiry = dt.date(2022, 6, 24)
	# strike_price = 452
	# call_put = "call"
	# side = "buy"
	# quantity = 1
	# order_type = "MARKET"
	# price = None
	# to_open = True
	# order_id = api.place_order(
	# 	symbol=symbol,
	# 	expiry=expiry,
	# 	strike_price=strike_price,
	# 	call_put=call_put,
	# 	side=side,
	# 	quantity=quantity,
	# 	order_type=order_type,
	# 	price=price,
	# 	to_open=to_open,
	# )
	# print(order_id)

	# NOTE Query order
	# order_id = 123456
	# order_info = api.query_order(order_id=order_id)

	# NOTE Cancel order
	# order_id = 123456
	# api.cancel_order(order_id=order_id)