from datetime import datetime, timedelta
import glob
import os
from typing import Literal
import zipfile

import pandas as pd
import requests


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
        if r.ok:
            return r.json()
        else:
            print(f"Request failed with status code {r.status_code}")
            return r.text

    def list_grid_regions(self, all_regions: bool = False) -> [dict]:
        """List of Grid Regions
        https://www.watttime.org/api-documentation/#list-of-grid-regions

        By default this endpoint delivers a list of regions to which you have access.
        Optionally, it can return a list of all grid regions where WattTime has data coverage.

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
        if r.ok:
            return r.json()
        else:
            print(f"Request failed with status code {r.status_code}")
            return r.text

    def real_time_emissions_index(
        self,
        bal_auth_abbr: str = None,
        lati_long: (float, float) = None,
        style: Literal["percent", "moer", "all"] = None,
        ) -> dict:
        """Real-time Emissions Index
        https://www.watttime.org/api-documentation/#real-time-emissions-index
        Query by balancing authority abbreviation OR latitude/longitude, NOT all three.

        Args:
            bal_auth_abbr (str): Balancing authority abbreviation. Example: 'CAISO_NORTH'
            lati_long (tuple): Tuple containing (latitude, longitude) as float values
            style (str): Units in which to provide realtime marginal emissions. Choices are 'percent', 'moer' or 'all'.
                Note: 'moer' option is available only to users with PRO subscriptions.

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
        if r.ok:
            return r.json()
        else:
            print(f"Request failed with status code {r.status_code}")
            return r.text

    def grid_emissions_data(
        self,
        bal_auth_abbr: str = None,
        lati_long: (float, float) = None,
        style: Literal["percent", "moer", "all"] = None,
        start_and_end_time: ("start_timestamp", "end_timestamp") = None,
        moerversion: str = None
        ) -> dict:
        """Real-time Emissions Index
        Restricted to customers with ANALYST or PRO subscriptions. Data can be previewed by setting bal_auth_abbr = 'CAISO_NORTH'
        https://www.watttime.org/api-documentation/#grid-emissions-data

        Query by balancing authority abbreviation OR latitude/longitude, NOT all three.

        Args:
            bal_auth_abbr (str): Balancing authority abbreviation. Example: 'CAISO_NORTH'
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
        if r.ok:
            return r.json()
        else:
            print(f"Request failed with status code {r.status_code}")
            return r.text

    def historical_emissions(
        self,
        bal_auth_abbr: str,
        filename: str = "historical",
        extract_files: bool = False,
        concatenate: bool = False,
        moerversion: Literal["latest", "all"] = "all",
        ) -> None:
        """Historical Emissions
        Restricted to customers with ANALYST or PRO subscriptions. Data can be previewed by setting bal_auth_abbr = 'CAISO_NORTH'
        https://www.watttime.org/api-documentation/#historical-emissions

        Obtain a zip file containing monthly .csv files with the MOER values (e.g. CO2 lbs/MWh)
        and timestamps for a given region for (up to) the past two years.
        Options to unzip and combine CSV files included.

        Access to this endpoint is restricted to customers with ANALYST or PRO subscriptions.
        However, if you don't yet have a subscription, you can preview the available data by
        providing CAISO_NORTH as the ba for your requests.

        This method will create a folder called "output" in the working directory.
        Files created by this method will be saved to the "output" folder.

        Args:
            bal_auth_abbr (str): Balancing authority abbreviation. Example: 'CAISO_NORTH'
            filename (str): Filename of the historical emissions zip file to be retrieved (exluding filetype extension)
            extract_files (bool): Option to extract zip files from API response.
            concatenate (bool): Option to combine extracted CSV files into a single CSV file (if 'extract_files' is True)
            moerversion (str): MOER version. Defaults to the latest version for a given region if omitted.

        Returns:
            None
        """
        if self._api_token_expire_dt > datetime.now():
            self._get_api_token()
        endpoint = self._host + "/historical"
        params = {"ba": bal_auth_abbr}
        if moerversion:
            params["version"] = moerversion

        r = requests.get(endpoint, headers=self._auth_header, params=params)
        try:
            # Save response as ZIP file
            working_dir = "output"  # possibly want to make this an optional argument
            filename = filename.split('.')[0]  # split text to clean filename in event user includes extension
            file_path = os.path.join(working_dir, filename)
            try:
                os.makedirs(working_dir)
            except FileExistsError:
                # directory already exists
                pass
            with open(f"{file_path}.zip", "wb") as binary_file:
                binary_file.write(r.content)
            if extract_files:
                # Extract zip file contents into folder
                with zipfile.ZipFile(file_path + ".zip", "r") as zip_ref:
                    zip_ref.extractall(file_path)
                if concatenate:
                    # Combine extracted CSV files into single file
                    all_files = glob.glob(f"{file_path}/*.csv")
                    combined_data = pd.concat([pd.read_csv(f) for f in all_files])
                    combined_data.to_csv(f"{file_path} (Combined Data).csv", index=False, encoding='utf-8-sig')
        except:
            print("Unable to save file.")
        return

    def emissions_forcast(
        self,
        bal_auth_abbr: str,
        starttime: str = None,
        endtime: str = None,
        extended_forecast: bool = None
        ) -> dict:
        """Emissions Forecast
        Restricted to customers with PRO subscriptions. Data can be previewed by setting bal_auth_abbr = 'CAISO_NORTH'
        https://www.watttime.org/api-documentation/#emissions-forecast

        Obtain a forecast of the MOERs (e.g. CO2 lbs/MWh) for a specified region.
        Omitting the starttime and endtime parameters will return the most recently generated forecast.
        Use the starttime and endtime parameters to obtain historical forecast data.

        TODO: If start to end time range is > 24 hours, automatically break up into multiple requests
        Args:
            bal_auth_abbr (str): Balancing authority abbreviation. Example: 'CAISO_NORTH'
            starttime (_type_, optional): Used to generate forcast between start and endtime. Format as "YYYY-MM-DDT-HH:MM:SS-%Z". Defaults to None.
            endtime (_type_, optional): Used to generate forcast between start and endtime. Format as "YYYY-MM-DDT-HH:MM:SS-%Z". Defaults to None.
            extended_forecast (bool, optional): Will provide a 72-hour forecast. Defaults to False.

        Returns:
            dict: Forecast of the MOERs (e.g. CO2 lbs/MWh) for a specified region.
        """
        if self._api_token_expire_dt > datetime.now():
            self._get_api_token()
        endpoint = self._host + "/forecast"
        params = {"ba": bal_auth_abbr}
        if starttime:
            params["starttime"] = starttime
        if endtime:
            params["endtime"] = endtime
        if extended_forecast:
            params["extended_forecast"] = extended_forecast

        r = requests.get(endpoint, headers=self._auth_header, params=params)
        if r.ok:
            return r.json()
        else:
            print(f"Request failed with status code {r.status_code}")
            return r.text

    def get_region_map_geometry(self) -> dict:
        """Grid Region Map Geometry
        Restricted to customers with ANALYST or PRO subscriptions
        https://www.watttime.org/api-documentation/#grid-region-map-geometry

        Provides a geojson of the grid region boundary for all regions that WattTime covers globally. 

        Returns:
            dict: A geojson response, that is a Feature Collection with properties that describe each BA,
                and multipolygon geometry made up of coordinates which define the boundary for each BA.
        """
        if self._api_token_expire_dt > datetime.now():
            self._get_api_token()
        endpoint = self._host + "/maps"
        r = requests.get(endpoint, headers=self._auth_header)
        if r.ok:
            return r.json()
        else:
            print(f"Request failed with status code {r.status_code}")
            return r.text
