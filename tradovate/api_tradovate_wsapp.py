# Author - Karan Parmar

"""
Tradovate websocket app that sends and receives the data
"""

# Importing built-in libraries
import os, json, time
from datetime import datetime, timedelta
from threading import Thread

# Importing third-party libraries
from websocket import WebSocketApp		# pip install websocket-client
import requests							# pip install requests
import pandas as pd						# pip install pandas

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
	def _read_json_file(file_path:str) -> dict:
		"""
		Parse and read json file\n
		"""
		with open(file_path) as f:
			data = json.load(f)
			f.close()
		return data

	@staticmethod
	def _save_json_file(file_path:str, data:dict) -> None:
		"""
		Writes json file\n
		"""
		with open(file_path, 'w') as f:
			json.dump(data,f, indent=4)
			f.close()
	
	@staticmethod
	def _is_token_expired(expiry_date:str) -> bool:
		"""
		Check if the generated token is expired or not\n
		expiryDate : str = datetime of the token follows (yyyy-mm-ddTHH:MM:SSz)\n
		"""
		expiry = datetime.strptime(expiry_date[:-5], "%Y-%m-%dT%H:%M:%S")
		utc_time = datetime.strptime(datetime.now().utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "%Y-%m-%dT%H:%M:%S")
		return utc_time >= (expiry - timedelta(minutes=10))

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
			
			token = requests.post(endpoint, json=params, headers=self._headers).json()
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
		self.ENDPOINT = self.SIMULATION_ENDPOINT if self.CREDS['account_type'].lower() in ['demo','testnet','sandbox', 'test'] else self.LIVE_ENDPOINT
		self.WSS_ENDPOINT = self.WS_DEMO_ENDPOINT if self.CREDS['account_type'].lower() in ['demo','testnet','sandbox', 'test'] else self.WS_LIVE_ENDPOINT

	def set_account(self):
		"""
		Set account ID and SPEC\n
		"""
		endpoint = self._get_endpoint() + '/account/list'
		response = requests.get(endpoint, headers=self._get_headers())
		account_info = response.json()[0]
		self.ACCOUNT_ID, self.ACCOUNT_SPEC = account_info['id'], account_info['name']

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

class TradovateClient:

	_is_connected = False
	_can_disconnect = False

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
		
		self._is_connected = True

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

				except KeyError:
					continue

	def _on_close(self, ws, closeCode, closeMessage):
		"""
		WS on close\n
		"""
		self._is_connected = False
		print("DISCONNECTED", closeCode, closeMessage)
	
	def _on_error(self, ws, error):
		print("WS_ERROR", error)

	def _on_ping(self, *args):
		# print(args,'ping')
		...

	def _on_pong(self, ws, pongMessage):
		# print(pongMessage,'pong')
		...

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
				if not self._is_connected: break

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
		self._can_disconnect = True
		self.WSAPP.close()

	# Public methods
	def connect(self) -> None:
		"""
		Connect to tradovate account
		"""
		def run_ws_thread():
			while True:
				if self._can_disconnect:
					self._disconnect()

				if not self._is_connected:
					self.login()
					self._create_websocket_app()
					self.WSAPP.run_forever(ping_interval=2)
					
		t1 = Thread(target=run_ws_thread, daemon=False)
		t1.start()

	def log(self, log_type:str, message:str) -> None:
		"""
		"""
		...

	def get_account_info(self) -> dict:
		"""
		Get connected account information\n
		"""
		return {}

	def get_account_balance(self) -> float:
		"""
		Get realtime account balance\n
		"""
		return float(1)
	
	def get_candle_data(self, symbol:str, timeframe:str, period:str='2d') -> pd.DataFrame:
		"""
		Get candle data from the API\n
		"""
		return

	def place_order(self, symbol:str, side:str, quantity:int, order_type:str="MARKET", price:float=...) -> int:
		"""
		"""
		...

	def place_bracket_order(self, symbol:str, side:str, quantity:int, order_type:str="MARKET", price:float=..., stoploss:str=..., targetprofit:float=...) -> tuple[int, int, int]:
		"""
		"""
		...

	def query_order(self, order_id:int) -> dict:
		"""
		"""
		return {}

	def cancel_order(self, order_id:int) -> None:
		"""
		"""
		...

class TradovateWrapper:
	
	# Invoke methods
	def on_order_placed(self, symbol:str, response:dict) -> None:
		...

	def on_order_filled(self, symbol:str, response:dict) -> None:
		...

	def on_order_canceled(self, symbol:str, response:dict) -> None:
		...

	def on_order_rejected(self, symbol:str, response:dict) -> None:
		...

class TradovateWSAPP(TradovateAuth, TradovateClient, TradovateWrapper):

	ID = "VT_TRADOVATE_API_WS"
	AUTHOR = "Variance Technologies"
	EXCHANGE = "SMART"
	BROKER = "TRADOVATE"
	MARKET = "FUTURES"
	
	def __init__(self, creds:dict):

		self.CREDS = creds

		self.set_user_credentials(creds)

if __name__ == "__main__":

	with open("creds_tradovate.json") as f:
		creds = json.load(f)
		f.close()

	api = TradovateWSAPP(creds=creds)
