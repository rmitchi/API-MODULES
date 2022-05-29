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
	
	ID = "VT_BINANCE_SPOT_API_REST"
	AUTHOR = "Variance Technologies"
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
				testnet=True if self.CREDS['account_type'].lower() in ['testnet','sandbox','demo'] else False
			)

	def get_asset_balance(self, asset:str='USDT') -> float:
		"""
		Returns free asset balance for given asset\n
		"""
		return self.client.get_asset_balance(asset=asset)

	def get_candle_data(self, symbol:str, timeframe:str, period:str='1d') -> pd.DataFrame:
		"""
		Returns historcal klines from past for given symbol and interval\n
		"""
		if period[-1] == 'd':
			pastDays = int(period[:-1])
		start_str=str((pd.to_datetime('today')-pd.Timedelta(str(pastDays)+' days')).date())
		df = pd.DataFrame(self.client.get_historical_klines(symbol=symbol,start_str=start_str,interval=timeframe))
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

if __name__ == "__main__":

	creds = {
		"api_key":"fa9jqiAMACRIt4eNiWGeDBPRc7DP2hrbYmVwNh8EN9qgJfuP2AfOwy1jyCBoyda3",
		"api_secret":"XJn71It6IBfIqonToPK7GrxNCfjuyWeWqUccmJOXGDO9h7NWJONBQpkbfcc66oV3",
		"testnet":True
	}

	api = BinanceSPOTAPIREST(creds)
	api.connect()

	# NOTE Get asset balance
	# asset = 'USDT'
	# assetBalance = api.get_asset_balance(asset=asset)
	# print(assetBalance)

	# NOTE Get candle data
	# symbol = 'BTCUSDT'
	# timeframe = '1m'
	# df = api.get_candle_data(symbol=symbol, timeframe=timeframe, period='1d')
	# print(df)