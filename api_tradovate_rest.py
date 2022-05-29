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

	@staticmethod
	def _save_json_file(filePath:str, data:dict) -> None:
		"""
		Writes json file\n
		"""
		with open(filePath,'w') as f:
			json.dump(data,f,indent=4)
			f.close()
	
	@staticmethod
	def _is_token_expired(expiryDate:str) -> bool:
		"""
		Check if the generated token is expired or not\n
		expiryDate : str = datetime of the token follows (yyyy-mm-ddTHH:MM:SSz)\n
		"""
		expiry = datetime.strptime(expiryDate[:-5],"%Y-%m-%dT%H:%M:%S")
		utcTime = datetime.strptime(datetime.now().utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"%Y-%m-%dT%H:%M:%S")
		return utcTime >= (expiry - timedelta(minutes=10))

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
			
			response = requests.post(endpoint,json=params,headers=self._headers)
			return response.json()

		except Exception as e:
			_ = f"error connecting to broker, {e}"
			raise Exception(_)

	# Public methods
	def set_user_credentials(self, creds:dict) -> None:
		"""
		Sets user's credential info\n
		"""
		self.TOKEN_PATH = "tradovate_access_token.json"
		
		self.ACCOUNT_ID = None
		self.ACCOUNT_SPEC = None
		self.USERNAME = creds['username']
		self.PASSWORD = creds['password']
		self.APP_ID = creds['app_id']
		self.APP_VERSION = creds['app_version']
		self.API_KEY = creds['api_key']
		self.API_SECRET = creds['api_secret']
		self.UUID = creds['uuid']
		self.ENDPOINT = self.SIMULATION_ENDPOINT if self.CREDS['account_type'].lower() in ['demo','testnet','sandbox'] else self.LIVE_ENDPOINT

	def set_account(self):
		"""
		Set account ID and SPEC\n
		"""
		endpoint = self._get_endpoint() + '/account/list'
		response = requests.get(endpoint,headers=self._get_headers())
		accountInfo = response.json()[0]
		self.ACCOUNT_ID, self.ACCOUNT_SPEC = accountInfo['id'], accountInfo['name']

	def login(self) -> None:
		"""
		Log into tradovate account with access token\n
		"""
		if os.path.exists(self.TOKEN_PATH):
			token = self._read_json_file(self.TOKEN_PATH)

			# CHECK IF EXPIRED
			if self._is_token_expired(token['expirationTime']):
				self._generate_access_token()
			
			try:
				self.ACCESS_TOKEN = token['accessToken']
				self.MD_ACCESS_TOKEN = token['mdAccessToken']

				if not all([self.ACCOUNT_ID, self.ACCOUNT_SPEC]):
					self.set_account()

			except Exception as e:
				print("Error in token",e)
				return self.login()

		else:
			token = self._generate_access_token()
			self._save_json_file(self.TOKEN_PATH, token)
			return self.login()

class TradovateEquityRESTAPI(TradovateAuth):

	ID = "VT_TRADOVATE_EQUITY_API_REST"
	AUTHOR = "Variance Technologies"
	EXCHANGE = "SMART"
	BROKER = "TRADOVATE"
	MARKET = "FUTURES"

	def __init__(self, creds:dict):

		self.CREDS = creds

		self.set_user_credentials(creds)

	# Public methods
	def connect(self) -> None:
		"""
		Connect to Tradovate equity account\n
		"""
		self.login()

	def get_account_info(self) -> dict:
		"""
		Get account info\n
		Returns: 
			accountInfo : dict = information of current account, NOTE This is sensetive info, should not be shared
		"""
		endpoint = self._get_endpoint() + '/account/list'
		response = requests.get(endpoint, headers=self._get_headers())
		accountDetails = response.json()[0]
		return accountDetails

	def get_candle_data(self, symbol:str, timeframe:str, period:str='1d') -> pd.DataFrame:
		"""
		Get realtime candlestick data\n
		symbol		: str 	= 	symbol of the ticker\n
		timeframe	: str 	= 	timeframe of the candles\n
		period		: str	=	period of the data\n
		"""
		pass

	def place_order(
			self, 
			symbol:str, 
			side:str, 
			quantity:int, 
			orderType:str='MARKET', 
			price:float=None,
			**options
		) -> int:
		"""
		Place order for options in broker server\n
		Arguments:
			symbol : str = symbol of the ticker
			side : str = side of the order execution
			quantity : int = quantity to trade
			limitPrice : float = limit price to set limit order (only for limit order)
			orderType : str = type of order (default market)
			\n
		Returns:
			orderId : int = id of the order
		"""
		body = {
			"accountSpec": self.ACCOUNT_SPEC,
			"accountId": self.ACCOUNT_ID,
			"action": side.title(),
			"symbol": symbol.upper(),
			"orderQty": int(quantity),
			"orderType": orderType.title(),
			"isAutomated": True 
		}
		if orderType.lower() == 'limit': 
			body['price'] = price
			if options.get('expirationTime'):
				body['timeInForce'] = 'GTD'
				body['expireTime'] = options['expireTime']

		if orderType.lower() == 'stop': 
			body['stopPrice'] = price
			body['timeInForce'] = 'Day'
		
		endpoint = self._get_endpoint() + '/order/placeorder/'
		response = requests.post(endpoint,json=body,headers=self._get_headers()).json()
		print(response.json())
		return response.json()['orderId']
		
	def place_oco_order(
			self, 
			symbol:str, 
			side:str, 
			quantity:int, 
			stoploss:float, 
			targetprofit:float
		) -> tuple[int, int]:
		"""
		Places an OCO (One Cancels Other) order in broker account\n
		Arguments:
			symbol : str = symbol of the ticker
			side : str = side of the order execution
			quantity : int = quantity to trade
			stoploss : float = stoploss absolute price for the symbol
			profitTarget : float = profittarget absolute price for the symbol
			\n
		Returns:
			stoplossId, takeprofitId : tuple = id of stoploss and takeprofit according will be returned
		"""
		oco = {
			"action":side.title(),
			"orderType":"Limit",
			"price":targetprofit
		}

		body = {
			"accountSpec": self.ACCOUNT_SPEC,
			"accountId": self.ACCOUNT_ID,
			"action": side.title(),
			"symbol": symbol.upper(),
			"orderQty": quantity,
			"orderType": "Stop",
			"stopPrice":stoploss,
			"isAutomated": True,
			"other":oco
		}

		endpoint = self._get_endpoint() + '/order/placeoco'
		response = requests.post(endpoint,json=body,headers=self._get_headers()).json()
		slId, tpId = response['orderId'], response.json()['ocoId']
		return slId, tpId

	def place_strategy_order(
			self, 
			symbol:str, 
			side:str, 
			quantity:int, 
			orderType:str="MARKET", 
			limitPrice:float=None, 
			stoploss:float=None, 
			targetprofit:float=None, 
			**options
		):
		"""
		Places strategy bracket order of entry and exit oco\n
		"""
		params = {
			"entryVersion":{
				"orderQty":1,
				"orderType":orderType.title()
			},
			"brackets":[
				{
					"qty":quantity,
					"profitTarget":targetprofit * (1 if side == 'buy' else -1),
					"stopLoss":stoploss * (-1 if side == 'buy' else 1),
					"trailingStop":False
				}
			]
		}

		if orderType.upper() == "LIMIT":
			params['entryVersion']['price'] = limitPrice
			if options.get('expireTime'):
				params['entryVersion']['timeInForce'] = 'GTD'
				params['entryVersion']['expireTime'] = options['expireTime']

		body = {
			"accountId":self.ACCOUNT_ID,
			"accountSpec":self.ACCOUNT_SPEC,
			"symbol":symbol,
			"action":side.title(),
			"orderStrategyTypeId":2,
			"params":json.dumps(params)
		}

		endpoint = self._get_endpoint() + '/orderstrategy/startorderstrategy'

		response = requests.post(endpoint, json=body, headers=self._get_headers())

		try:
			response = response.json()
			# {'orderStrategy': {'id': 3851683794, 'accountId': 614976, 'timestamp': '2022-05-12T11:47:15.809Z', 'contractId': 2553034, 'orderStrategyTypeId': 2, 'action': 'Sell', 'params': '{"entryVersion": {"orderQty": 1, "orderType": "Limit", "price": 3905}, "brackets": [{"qty": 1, "profitTarget": -1, "stopLoss": 3, "trailingStop": false}]}', 'status': 'ActiveStrategy', 'archived': False, 'senderId': 295323, 'userSessionId': 73808620}}
			return response

		except Exception:
			pass

		return

	def cancel_order(self, orderId:int) -> tuple[bool, str]:
		"""
		Cancels order by orderId\n
		Arguments:
			orderId : int = id of the order to cancel
		"""
		try:
			body = {
				"orderId":orderId,
				"isAutomated":True
			}

			endpoint = self._get_endpoint() + '/order/cancelorder'
			response = requests.post(endpoint,json=body,headers=self._get_headers())
			try:
				cancelDetatils = response.json()
				cancelStatus = False if ('failureReason' in cancelDetatils) else True
				return cancelStatus, cancelDetatils

			except Exception:
				return False, 'tooLate'

		except Exception as e:
			raise Exception(f"exception in cancelling order : {e}")

	def query_order(self, orderId:int) -> dict:
		"""
		Queries order by orderId\n
		Arguments:
			orderId : int = id of the order for query
			\n
		Returns:
			status : str = status of the queried order
		"""
		try:
			endpoint = self._get_endpoint() + '/order/item'
			params = {
				'id':orderId,
			}
			return requests.get(endpoint, params=params, headers=self._get_headers()).json()

		except Exception as e:
			raise Exception(f"exception in order query : {e}")

if __name__ == "__main__":

	with open("creds_tradovate.json") as f:
		creds = json.load(f)
		f.close()

	api = TradovateEquityRESTAPI(creds=creds)
	api.connect()

	# NOTE Get account info
	# accountInfo = api.get_account_info()
	# print(accountInfo)

	# NOTE Place order
	# orderId = api.place_order(
	# 	symbol='ESM2',
	# 	side='buy',
	# 	quantity=1,
	# 	orderType="MARKET",
	# 	price=None,
	# 	expireTime=None			# string YYYY-mm-ddTHH:MM:SST (Zulu time, is also UTC time)
	# )

	# NOTE Place oco order
	# orderId, ocoId = api.place_oco_order(
	# 	symbol='ESM2',
	# 	side='sell',
	# 	quantity=1,
	# 	stoploss=4203,			# stoploss is in limit price
	# 	targetprofit=4205		# targetprofit is in limit price
	# )

	# NOTE Place strategy order
	# strategyId = api.place_strategy_order(
	# 	symbol='ESM2',
	# 	side='buy',
	# 	quantity=1,
	# 	orderType='MARKET',
	# 	limitPrice=4000,
	# 	stoploss=3,				# stoploss is in points
	# 	targetprofit=1,			# targetprofit is in point
	# 	expireTime=None			# string YYYY-mm-ddTHH:MM:SST (Zulu time, is also UTC time)
	# )
	# print(strategyId)

	# NOTE Cancel order
	# orderId = 123456
	# api.cancel_order(orderId)

	# NOTE Query order info
	# orderId = 123456
	# orderQuery = api.query_order(orderId)
	# print(orderQuery)