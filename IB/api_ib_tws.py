# Author - Variance Technologies Pvt. Ltd.

"""
Interactive Brokers TWS API

	To use this API the user must download TWS (Trader workstation) desktop software and run it in the machine. This API is simply a bridge to the TWS desktop app. 
	It will communicate to assigned port. The port might be different based on the configurations

"""

# Importing third-party libraries
import pandas as pd 				# pip install pandas

class TWSIBAPI:

	ID = "VT_TWS_IB_API"
	NAME = "Interactive Brokers TWS API"
	AUTHOR = "Variance Technologies Pvt. Ltd."
	TYPE = "BROKER_API"

	def __init__(self, creds: dict):
		
		self.CREDS = creds

	# Public methods
	def connect(self) -> None:
		"""
		"""
		...

	def get_account_info(self) -> dict:
		"""
		"""
		...

	def get_account_balance(self) -> float:
		"""
		"""
		...

	def get_contract_info(self) -> dict:
		"""
		"""
		...

	def get_candle_data(self) -> pd.DataFrame:
		"""
		"""
		...

	def place_order(self) -> int:
		"""
		"""
		...

	def query_order(self, order_id: int) -> dict:
		"""
		"""
		...

	def cancel_order(self, order_id: int) -> None:
		"""
		"""
		...

if __name__ == "__main__":

	creds = {
		"host": "127.0.0.1",
		"port": 7497,
		"client_id": 1
	}

	API = TWSIBAPI(creds=creds)
	API.connect()

	# NOTE Get account info
	# account_info = API.get_account_info()
	# print(account_info)

	# NOTE Get account balance
	# account_balance = API.get_account_balance()
	# print(account_balance)

	# NOTE Get contract info
	# contract_info = API.get_contract_info()
	# print(contract_info)