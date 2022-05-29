# Author - Karan Parmar

"""
TRADOVATE WEBSOCKET API
"""

# Importing built-in libraries
import os, json, time
from datetime import datetime, timedelta
from threading import Thread

# Importing third-party libraries
import requests								# pip install requests
import pandas as pd							# pip install pandas
from websocket import WebSocketApp			# pip install websocket-client

class TradovateAuth:
	
	LIVE_ENDPOINT = "https://live.tradovateapi.com"
	SIMULATION_ENDPOINT = "https://demo.tradovateapi.com"

	WS_DEMO_ENDPOINT = "wss://demo.tradovateapi.com/v1/websocket"
	WS_LIVE_ENDPOINT = "wss://live.tradovateapi.com/v1/websocket"

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
			
			token = requests.post(endpoint,json=params,headers=self._headers).json()
			# print(token)
			return token

		except Exception as e:
			_ = f"error connecting to broker, {e}"
			raise Exception(_)

	# Public methods
	def set_user_credentials(self, creds:dict) -> None:
		"""
		Sets user's credential info\n
		"""
		self.TOKEN_PATH = "tradovate_access_token.json"
		
		# Setting account details
		self.ACCOUNT_ID = None
		self.ACCOUNT_SPEC = None
		self.USERNAME = creds['username']
		self.PASSWORD = creds['password']
		self.APP_ID = creds['app_id']
		self.APP_VERSION = creds['app_version']
		self.API_KEY = creds['api_key']
		self.API_SECRET = creds['api_secret']
		self.UUID = creds['uuid']

		# Setting endpoints
		self.ENDPOINT = self.SIMULATION_ENDPOINT if self.CREDS['account_type'].lower() in ['demo','testnet','sandbox'] else self.LIVE_ENDPOINT
		self.WSS_ENDPOINT = self.WS_DEMO_ENDPOINT if self.CREDS['account_type'].lower() in ['demo','testnet','sandbox'] else self.WS_LIVE_ENDPOINT

	def set_account(self):
		"""
		Set account ID and SPEC\n
		"""
		endpoint = self._get_endpoint() + '/account/list'
		response = requests.get(endpoint, headers=self._get_headers())
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
				token = self._generate_access_token()
				self._save_json_file(self.TOKEN_PATH, token)
				return self.login()
			
			try:
				self.ACCESS_TOKEN = token['accessToken']
				self.MD_ACCESS_TOKEN = token['mdAccessToken']

				if not all([self.ACCOUNT_ID, self.ACCOUNT_SPEC]):
					self.set_account()

			except Exception as e:
				print("Error in local token",e)
				return self.login()

		else:
			token = self._generate_access_token()
			self._save_json_file(self.TOKEN_PATH, token)
			return self.login()

class TradovateWSAPP:

	_isConnected = False
	_canDisconnect = False

	def _create_websocket_app(self) -> None:
		"""
		Creates a websocket app\n
		"""
		self.WSAPP = WebSocketApp(
			url=self.WSS_ENDPOINT,
			on_open=self._on_open,
			on_message=self._on_message,
			on_close=self._on_close,
			on_error=self._on_error,
			on_ping=self._on_ping,
			on_pong=self._on_pong
		)
		
		self._isConnected = True

	def _on_open(self,raw):
		"""
		Authenticates on websocket open\n
		"""
		body = f"authorize\n1\n\n{self.ACCESS_TOKEN}"
		self.WSAPP.send(body)
		self.log("WS CONNECT","AUTHORIZED")
		
		# Starting heartbeat
		self._start_heartbeat()
	
	def _on_message(self, ws, raw):
		"""
		On message tick\n
		"""
		print(raw)

	def _on_close(self, ws, closeCode, closeMessage):
		"""
		WS on close\n
		"""
		self._isConnected = False
		print("DISCONNECTED", closeCode, closeMessage)
	
	def _on_error(self, ws, error):
		print("WS_ERROR", error)

	def _on_ping(self, *args):
		# print(args,'ping')
		pass

	def _on_pong(self, ws, pongMessage):
		# print(pongMessage,'pong')
		pass

	# Custom methods
	def _subscribe_user_sync(self):
		"""
		Subscribes user sync from websocket to get all account interactions\n
		"""
		self.WSAPP.send(f"user/syncrequest\n10")

	def _start_heartbeat(self):
		"""
		Starts heartbeat to keep the connection alive\n
		"""
		def heartbeat():
			while True:
				if not self._isConnected: break

				time.sleep(2)
				try:
					self.WSAPP.send(json.dumps([]))
				except Exception:
					continue

		t1 = Thread(target=heartbeat, daemon=False)
		t1.start()

	def _disconnect(self):
		"""
		Disconnect websocket\n
		"""
		self._canDisconnect = True
		self.WSAPP.close()

	def _connect(self):
		"""
		Connect and reconnect\n
		"""
		def run_ws_thread():
			while True:
				if self._canDisconnect:
					self._disconnect()

				if not self._isConnected:
					self.login()
					self._create_websocket_app()
					self.WSAPP.run_forever(ping_interval=2)
					
		t1 = Thread(target=run_ws_thread, daemon=False)
		t1.start()

class TradovateWSAPI(TradovateAuth, TradovateWSAPP):

	ID = "VT_TRADOVATE_API_WS"
	AUTHOR = "Variance Technologies"
	EXCHANGE = "SMART"
	BROKER = "TRADOVATE"
	MARKET = "FUTURES"

	def __init__(self, creds:dict):

		self.CREDS = creds

		self.set_user_credentials(creds)

	# Helper methods
	@staticmethod
	def log(message:str, logType:str) -> None:
		"""
		Logs interactions\n
		"""
		print(f"{logType}\t:\t{message}")

	# Private methods
	def _on_message(self, ws, raw):
		"""
		"""
		if len(raw) > 1:
			data = json.loads(raw[1:])

			for response in data:
				
				try:
					# Subscribe to user sync
					if response.get('i') and response['i'] == 1:
						self._subscribe_user_sync()

					# To get notification of order
					if response['d']['entityType'] == 'executionReport': 
						
						if response['d']['eventType'] == 'Created':
							
							if response['d']['entity']['ordStatus'] == 'Working':
								# NOTE ADD WORKING SNIPPET
								pass

							elif response['d']['entity']['ordStatus'] == 'Filled':
								# NOTE ADD FILLED SNIPPET
								pass

							elif response['d']['entity']['ordStatus'] == 'Rejected':
								# NOTE ADD REJECTED SNIPPET
								pass
							
							elif response['d']['entity']['ordStatus'] == 'Canceled':
								# NOTE ADD CANCELLATION SNIPPET
								pass

						print(response)
						print()

				except KeyError:
					continue

	# Public methods
	def connect(self) -> None:
		"""
		Connect to tradovate websocket\n
		"""
		self._connect()

	def place_order(
			self,
			symbol:str,
			side:str,
			quantity:str,
			orderType:str="MARKET",
			price:float=None,
			**options,
		) -> None:
		"""
		Place order for options in broker server\n
		Arguments:\n
			symbol : str = symbol of the ticker\n
			side : str = side of the order execution\n
			quantity : int = quantity to trade\n
			limitPrice : float = limit price to set limit order (only for limit order)\n
		"""
		commandId = options.get('commandId') or 5
		body = {
			"accountSpec": self.ACCOUNT_SPEC,
			"accountId": self.ACCOUNT_ID,
			"action": side.title(),
			"symbol": symbol.upper(),
			"orderQty": int(quantity),
			"orderType": orderType.title(),
			"isAutomated": True,
		}
		if options.get('expireTime'):
			body['timeInForce'] = 'GTD'
			body['expireTime'] = options['expireTime']
		
		if orderType.lower() == 'limit':
			body['price']= price
			
		if orderType.lower() == 'stop':
			body['stopPrice'] = price
			del body['price']

		self.WSAPP.send(f"order/placeorder\n{commandId}\n\n{json.dumps(body)}")

	def _place_oco_order(
			self,
			symbol:str,
			side:str,
			quantity:int,
			stoploss:float,
			targetprofit:float,
			**options
		) -> None:
		"""
		Places an OCO (One Cancels Other) order in broker account\n
		Arguments:\n
			symbol 			: str 	= symbol of the ticker\n
			side 			: str 	= side of the order execution\n
			quantity 		: int 	= quantity to trade\n
			stoploss 		: float = stoploss absolute price for the symbol\n
			targetparget 	: float = profittarget absolute price for the symbol\n
			"""
		commandId = options.get('commandId') or 6
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
		self.WSAPP.send(f"order/placeoco\n{commandId}\n\n{json.dumps(body)}")

	def place_strategy_order(
			self, 
			symbol:str,
			side:str,
			quantity:int,
			orderType:str="MARKET",
			price:float=None,
			stoploss:float=None,
			targetprofit:float=None,
			**options
		) -> None:
		"""
		Places strategy order via websocket\n
		"""
		commandId = options.get('commandId') or 7
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
			params['entryVersion']['price'] = price
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

		self.WSAPP.send(f"orderstrategy/startorderstrategy\n{commandId}\n\n{json.dumps(body)}")

	def cancel_order(self,orderId:int):
		"""
		Cancel the order via websocket\n
		"""
		commandId = 4
		body = {
			"orderId":orderId,
			"isAutomated":True
		}
		self.WSAPP.send(f"order/cancelorder\n{commandId}\n\n{json.dumps(body)}")

	def get_websocket_connection_status(self):
		"""
		Returns connection status of websocket api\n
		"""
		return self._isConnected

if __name__ == "__main__":

	with open("creds_tradovate.json") as f:
		creds = json.load(f)
		f.close()

	api = TradovateWSAPI(creds)
	api.connect()