# WattTime-API-Wrapper
Python API wrapper for the WattTime API: https://www.watttime.org/api-documentation
## Key Features
- Full support for all endpoints and parameters.
- Automatically update API key once it has expired (every 30 mins).
- Built in rate limiting to comply with WattTime API ussage guidelines (3000 requests/5 mins)
- Increased performance by reusing [session object](https://docs.python-requests.org/en/master/user/advanced/#session-objects) accross requests.
- Additional QoL features to facilitate working with response data.

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
## Use the Client
#### Determine Grid Region
```
latitude = 33.844978
longitude = -118.387238
wt.determine_grid_region(latitude, longitude)
```

The output is similar to the following:
```
> {'abbrev': 'CAISO_LONGBEACH', 'name': 'California ISO Long Beach', 'id': 233}
```

- For a full list of ussage examples, see the [WattTime API Demo.ipynb](https://github.com/aarongzmn/watttime-api-wrapper/blob/main/WattTime%20API%20Demo.ipynb) notebook that has been included in this repository.
