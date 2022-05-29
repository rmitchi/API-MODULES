# Author - Karan Parmar

"""
ZERODHA EQUITY REST API
"""

class ZerodhaEquityRESTAPI:

	ID = "VT_ZERODHA_EQUITY_API_REST"
	AUTHOR = "Variance Technologies"
	EXCHANGE = "SMART"
	BROKER = "ZERODHA"
	MARKET = "EQUITY"

	def __init__(self, creds:dict):
		
		self.CREDS = creds

	# Public methods
	def connect(self) -> None:
		"""
		Connect to Zerodha equity account\n
		"""
		pass
