# WattTime-API-Wrapper
Python API wrapper for the WattTime API: https://www.watttime.org/api-documentation
## Key Features
- Full support for all endpoints and parameters.
- Automatically update API key once it has expired (every 30 mins).
- Built in rate limiting to comply with WattTime API ussage guidelines (3000 requests/5 mins)
- Increased performance by reusing [session object](https://docs.python-requests.org/en/master/user/advanced/#session-objects) accross requests.
- Additional ease of use features/tools to extend

# Register Account
```
from WattTime import WattTime


username = "{USERNAME}"
password = "{PASSWORD}"
email = "{EMAIL_ADDRESS}"
org = "{ORG_NAME}"
wt = WattTime.RegisterNewUser(username, password, email)
```

# Create a Client
- After you have registered for an account, save your username and password as environment variables.
```
from WattTime import WattTime
import os


username = os.getenv("WATTTIME_API_USERNAME")
password = os.getenv("WATTTIME_API_PASSWORD")

wt = WattTime.GridEmissionsInformation(username, password)
```
For a full list of ussage examples, see the included notebook called "[WattTime API Demo.ipynb](https://github.com/aarongzmn/watttime-api-wrapper/blob/main/WattTime%20API%20Demo.ipynb)".
