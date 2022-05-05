import requests
from datetime import datetime, timedelta
from typing import Literal


class RegisterNewUser:
    """Provide basic information to self register for an account.
    https://www.watttime.org/api-documentation/#register-new-user
    """
    def __init__(self, username: str, password: str, email: str, org: str = None):
        self.username = username
        self.password = password
        self.email = email
        self.org = org
        self.register()

    def register(self):
        register_url = "https://api2.watttime.org/v2/register"
        params = {
            "username": self.username,
            "password": self.password,
            "email": self.email,
            "org": self.org
        }
        r = requests.post(register_url, json=params)
        if r.ok and "ok" in r.json().keys():
            print("Account Created")
        else:
            if "error" in r.json().keys():
                print(f"Unable to create account: {r.json()['error']}")
            else:
                print(f"Unable to create account, see server response for details:\n{r.json()}")
        self.registration_response = r.json()
        return


class GridEmissionsInformation:
    """Use to interact with the WattTime API.
    API token is refreshed automatically (as needed).
    https://www.watttime.org/api-documentation/#grid-emissions-information
    """
    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password
        self._host = "https://api2.watttime.org/v2"
        self._get_api_token()

    def _get_api_token(self):
        """Token expires after 30 minutes. If a data call returns HTTP 401 error code,
        you will need to call /login again to receive a new token.
        """
        endpoint = self._host + "/login"
        r = requests.get(endpoint, auth=(self._username, self._password))
        if r.ok:
            self._api_token = r.json()["token"]
            self._auth_header = {"Authorization": f"Bearer {r.json()['token']}"}
            self._api_token_expire_dt = datetime.now() + timedelta(minutes=29)
        else:
            print("Login Failed")

    def determine_grid_region(self, latitude: float, longitude: float) -> dict:
        """Determine Grid Region
        https://www.watttime.org/api-documentation/#determine-grid-region

        Args:
            latitude (float): Latitude of device location
            longitude (float): Longitude of device location

        Returns:
            dict: Returns the details of the balancing authority (BA) serving that location, if known,
                or a Coordinates not found error if the point lies outside of known/covered BAs.
        """
        if self._api_token_expire_dt > datetime.now():
            self._get_api_token()
        endpoint = self._host + "/ba-from-loc"
        params = {"latitude": latitude, "longitude": longitude}
        r = requests.get(endpoint, headers=self._auth_header, params=params)
        return r.json()

    def list_grid_regions(self, all_regions: bool = False) -> [dict]:
        """List of Grid Regions
        https://www.watttime.org/api-documentation/#list-of-grid-regions

        Args:
            all_regions (bool): If 'all': 'true' is specified,
                the entire list of regions will be returned.

        Returns:
            [dict]: list of dictionaries containing region information.
        """
        if self._api_token_expire_dt > datetime.now():
            self._get_api_token()
        endpoint = self._host + "/ba-access"
        params = {"all": all_regions}
        r = requests.get(endpoint, headers=self._auth_header, params=params)
        return r.json()

    def real_time_emissions_index(self,
        bal_auth_abbr: str = None,
        lati_long: (float, float) = None,
        style: Literal["percent", "moer", "all"] = None,
        ) -> dict:
        """Real-time Emissions Index
        Query by balancing authority abbreviation OR latitude/longitude, NOT all three.
        https://www.watttime.org/api-documentation/#real-time-emissions-index

        Args:
            bal_auth_abbr (str): Balancing authority abbreviation.
            lati_long (tuple): Tuple containing (latitude, longitude) as float values
            style (str): Units in which to provide realtime marginal emissions. Choices are 'percent', 'moer' or 'all'.

        Returns:
            dict: Real-time data indicating the marginal carbon intensity for the local grid for the current time
        """
        if self._api_token_expire_dt > datetime.now():
            self._get_api_token()
        endpoint = self._host + "/index"
        params = {}
        if bal_auth_abbr:
            params["ba"] = bal_auth_abbr
        if lati_long:
            params["latitude"] = lati_long[0]
            params["longitude"] = lati_long[1]
        if style:
            params["style"] = style

        r = requests.get(endpoint, headers=self._auth_header, params=params)
        return r.json()

    def grid_emissions_data(self,
        bal_auth_abbr: str = None,
        lati_long: (float, float) = None,
        style: Literal["percent", "moer", "all"] = None,
        start_and_end_time: ("start_timestamp", "end_timestamp") = None,
        moerversion: str = None
        ) -> dict:
        """Real-time Emissions Index
        Query by balancing authority abbreviation OR latitude/longitude, NOT all three.
        https://www.watttime.org/api-documentation/#grid-emissions-data

        Args:
            bal_auth_abbr (str): Balancing authority abbreviation.
            lati_long (tuple): Tuple containing (latitude, longitude) as float values
            style (str): Units in which to provide realtime marginal emissions. Choices are 'percent', 'moer' or 'all'.
            start_and_end_time (tuple): Tuple containing (starttime, endtime) as string timestamps
            moerversion (str): MOER version. Defaults to the latest version for a given region if omitted.

        Returns:
            dict: Historical MOERS (e.g. CO2 lbs/MWh) for a specified grid region balancing authority or location
        """
        if self._api_token_expire_dt > datetime.now():
            self._get_api_token()
        endpoint = self._host + "/data"
        params = {}
        if bal_auth_abbr:
            params["ba"] = bal_auth_abbr
        if lati_long:
            params["latitude"] = lati_long[0]
            params["longitude"] = lati_long[1]
        if start_and_end_time:
            params["starttime"] = start_and_end_time[0]
            params["endtime"] = start_and_end_time[1]
        if style:
            params["style"] = style
        if moerversion:
            params["moerversion"] = moerversion

        r = requests.get(endpoint, headers=self._auth_header, params=params)
        return r.json()

    def historical_emissions(self,
        bal_auth_abbr: str = None,
        moerversion: Literal["latest", "all"] = "all",
        ) -> dict:
        """Historical Emissions
        Obtain a zip file containing monthly .csv files with the MOER values (e.g. CO2 lbs/MWh)
        and timestamps for a given region for (up to) the past two years.
        https://www.watttime.org/api-documentation/#historical-emissions

        Args:
            bal_auth_abbr (str): Balancing authority abbreviation.
            moerversion (str): MOER version. Defaults to the latest version for a given region if omitted.

        Returns:
            dict: 
        """
        if self._api_token_expire_dt > datetime.now():
            self._get_api_token()
        endpoint = self._host + "/historical"
        params = {}
        if bal_auth_abbr:
            params["ba"] = bal_auth_abbr
        if moerversion:
            params["version"] = moerversion

        r = requests.get(endpoint, headers=self._auth_header, params=params)
        return r.json()

    def emissions_forcast(self):
        pass

    def get_regional_map_geometry(self):
        pass
