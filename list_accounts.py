import os, json
from oandapyV20 import API
from oandapyV20.endpoints.accounts import AccountList

# 1. Read your practice token from env
token = os.getenv("OANDA_TOKEN")

# 2. Initialize the client in practice mode
client = API(access_token=token, environment="practice")

# 3. Create and send the AccountList request
req = AccountList()
resp = client.request(req)

# 4. Pretty-print the JSON so you can see your account IDs
print(json.dumps(resp, indent=2))
  