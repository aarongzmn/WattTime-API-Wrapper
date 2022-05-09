from datetime import datetime, timedelta
import glob
import os
import time
from typing import Literal
import warnings
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

    def register(self) -> dict:
        register_url = "https://api2.watttime.org/v2/register"
        params = {
            "username": self.username,
            "password": self.password,
            "email": self.email,
            "org": self.org
        }

        try:
            r = requests.post(register_url, json=params)
            if r.status_code == 400:
                # 400 indicates bad request, check parameters
                raise Exception(r.json()["error"])
            else:
                # Catch all other HTTP errors
                r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise

class GridEmissionsInformation:
    """Use to interact with the WattTime API.
    API token is refreshed automatically (as needed).
    https://www.watttime.org/api-documentation/#grid-emissions-information
    """
    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password
        self._host = "https://api2.watttime.org/v2"
        self._session = requests.Session()
        self._get_api_token()

        """
        Default API rate limit settings.
        https://www.watttime.org/api-documentation/#introduction
        """
        self._calls = 10  # Maximum number of API calls within time 'period'.
        self._period = 1  # Seconds before the rate limit resets.
        self._cushion = 1  #  Seconds to wait once rate limit is reached.
        self._timestamp_list = [time.time() - self._period] * self._calls

    def _get_api_token(self) -> None:
        """Token expires after 30 minutes. If a data call returns HTTP 401 error code,
        you will need to call /login again to receive a new token.
        This is to be called from the "_api_helper" method, is run before all API requests.
        """
        try:
            endpoint = self._host + "/login"
            r = self._session.get(endpoint, auth=(self._username, self._password))
            r.raise_for_status()
            self._api_token = r.json()["token"]
            self._session.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
            self._api_token_expire_dt = datetime.now() + timedelta(minutes=29)
        except requests.exceptions.HTTPError as e:
            raise

    def _rate_limiter(self) -> None:
        """This method assists with rate limiting API requests (if needed).
        This is to be called from the "_api_helper" method, is run before all API requests.
        """
        ts_now = time.time()
        request_count = len([ts for ts in self._timestamp_list if ts > (ts_now - self._period)])
        if request_count >= self._calls:
            rate_limit_cooldown = int(ts_now - self._timestamp_list[0]) + self._cushion
            # warnings.warn(f"API rate limit reached, waiting for reset in {rate_limit_cooldown} seconds")
            time.sleep(rate_limit_cooldown)
        self._timestamp_list = self._timestamp_list[1:] + [ts_now]
        return

    def _api_helper(self) -> None:
        """This method serves two purposes:
        1. It automatically refreshes API tokens when they are close to expiring.
        2. It applies rate limits to comply with the WattTime API limitations.
        This should be used before making API calls.

        TODO: This could possibly be implemented as a decorator.
        """
        if self._api_token_expire_dt > datetime.now():
            self._get_api_token()
        self._rate_limiter()

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
        params = {"latitude": latitude, "longitude": longitude}
        try:
            endpoint = self._host + "/ba-from-loc"
            self._api_helper()
            r = self._session.get(endpoint, params=params)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            raise Exception(r.json())

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
        params = {"all": all_regions}
        try:
            endpoint = self._host + "/ba-access"
            self._api_helper()
            r = self._session.get(endpoint, params=params)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            raise Exception(r.json())

    def real_time_emissions_index(
        self,
        balancing_auth: str = None,
        latitude: float = None,
        longitude: float = None,
        style: Literal["percent", "moer", "all"] = None,
        ) -> dict:
        """Real-time Emissions Index
        https://www.watttime.org/api-documentation/#real-time-emissions-index
        Query by balancing authority abbreviation OR latitude/longitude, NOT all three.

        Args:
            balancing_auth (str): Balancing authority abbreviation. Example: 'CAISO_NORTH'
            latitude (float): Latitude of device location
            longitude (float): Longitude of device location
            style (str): Units in which to provide realtime marginal emissions. Choices are 'percent', 'moer' or 'all'.
                Note: 'moer' option is available only to users with PRO subscriptions.

        Returns:
            dict: Real-time data indicating the marginal carbon intensity for the local grid for the current time
        """
        params = {}
        if balancing_auth and (latitude or longitude):
            raise Exception("Query by balancing authority OR latitude/longitude, NOT all three.")
        elif balancing_auth:
            params["ba"] = balancing_auth
        elif latitude and longitude:
            params["latitude"] = latitude
            params["longitude"] = longitude
        else:
            raise Exception("One of balancing authority OR latitude and longitude required")
        if style:
            params["style"] = style
        try:
            endpoint = self._host + "/index"
            self._api_helper()
            r = self._session.get(endpoint, params=params)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            raise Exception(r.json())

    def grid_emissions_data(
        self,
        balancing_auth: str = None,
        latitude: float = None,
        longitude: float = None,
        style: Literal["percent", "moer", "all"] = "all",
        starttime: str = None,
        endtime: str = None,
        moerversion: str = None
        ) -> dict:
        """Real-time Emissions Index
        https://www.watttime.org/api-documentation/#grid-emissions-data
        Restricted to customers with ANALYST or PRO subscriptions.
        Data can be previewed by setting balancing_auth = 'CAISO_NORTH'
        Query by balancing authority abbreviation OR latitude and longitude, NOT all three.

        Args:
            balancing_auth (str): Balancing authority abbreviation. Example: 'CAISO_NORTH'
            latitude (float): Latitude of device location
            longitude (float): Longitude of device location
            style (str): Units in which to provide realtime marginal emissions. Choices are 'percent', 'moer' or 'all'.
            starttime (str): ISO 8601 timestamp (inclusive) - defines the first point_time of the batch. Must be provided in endtime is also provided.
            endtime (str): ISO 8601 timestamp (inclusive) - if endtime is omitted, endtime is equal to the current time.
            moerversion (str): MOER version. Defaults to the latest version for a given region if omitted.

        Returns:
            dict: Historical MOERS (e.g. CO2 lbs/MWh) for a specified grid region balancing authority or location
        """
        params = {}
        if balancing_auth and (latitude or longitude):
            raise Exception("Query by balancing authority OR latitude/longitude, NOT all three.")
        elif balancing_auth:
            params["ba"] = balancing_auth
        elif latitude and longitude:
            params["latitude"] = latitude
            params["longitude"] = longitude
        else:
            raise Exception("One of balancing authority OR latitude and longitude required")
        if style:
            params["style"] = style
        if endtime and not starttime:
            raise Exception("Starttime must be provided if endtime is also provided.")
        if starttime:
            params["starttime"] = starttime
        if endtime:
            params["endtime"] = endtime
        if moerversion:
            params["moerversion"] = moerversion
        try:
            endpoint = self._host + "/data"
            self._api_helper()
            r = self._session.get(endpoint, params=params)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            raise Exception(r.json())

    def historical_emissions(
        self,
        balancing_auth: str,
        filename: str = "historical",
        extract_files: bool = False,
        concatenate: bool = False,
        moerversion: Literal["latest", "all"] = "all",
        ) -> str:
        """Historical Emissions
        https://www.watttime.org/api-documentation/#historical-emissions
        Restricted to customers with ANALYST or PRO subscriptions.
        Data can be previewed by setting balancing_auth = 'CAISO_NORTH'

        Obtain a zip file containing monthly .csv files with the MOER values (e.g. CO2 lbs/MWh)
        and timestamps for a given region for (up to) the past two years.
        Options to unzip and combine CSV files included.

        This method will create a folder called "output" in the working directory.
        Files created by this method will be saved to the "output" folder.

        Args:
            balancing_auth (str): Balancing authority abbreviation. Example: 'CAISO_NORTH'
            filename (str): Filename of the historical emissions zip file to be retrieved (exluding filetype extension)
            extract_files (bool): Option to extract zip files from API response.
            concatenate (bool): Option to combine extracted CSV files into a single CSV file (if 'extract_files' is True)
            moerversion (str): MOER version. Defaults to the latest version for a given region if omitted.

        Returns:
            str: Absolute path where file(s) will be saved.
        """
        params = {"ba": balancing_auth}
        if moerversion:
            params["version"] = moerversion
        try:
            endpoint = self._host + "/historical"
            self._api_helper()
            r = self._session.get(endpoint, params=params)
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise Exception(r.json())

        # Save response as ZIP file
        working_folder = "output"  # possibly want to make this an optional argument
        filename = filename.split('.')[0]  # split text to clean filename in event user includes extension
        rel_path = os.path.join(working_folder, filename)
        try:
            os.makedirs(working_folder)
        except FileExistsError:
            # directory already exists
            pass
        with open(f"{rel_path}.zip", "wb") as binary_file:
            binary_file.write(r.content)
        if extract_files:
            # Extract zip file contents into folder
            with zipfile.ZipFile(rel_path + ".zip", "r") as zip_ref:
                zip_ref.extractall(rel_path)
            if concatenate:
                # Combine extracted CSV files into single file
                all_files = glob.glob(f"{rel_path}/*.csv")
                combined_data = pd.concat([pd.read_csv(f) for f in all_files])
                csv_filename = f"{rel_path} (Combined Data).csv"
                combined_data.to_csv(csv_filename, index=False, encoding='utf-8-sig')
                return os.path.join(os.getcwd(), csv_filename)
            return os.path.join(os.getcwd(), working_folder, filename)
        return os.path.join(os.getcwd(), working_folder, filename + ".zip")

    def emissions_forcast(
        self,
        balancing_auth: str,
        starttime: str = None,
        endtime: str = None,
        extended_forecast: bool = None
        ) -> dict:
        """Emissions Forecast
        https://www.watttime.org/api-documentation/#emissions-forecast
        Restricted to customers with PRO subscriptions. Data can be previewed by setting balancing_auth = 'CAISO_NORTH'
        

        Obtain a forecast of the MOERs (e.g. CO2 lbs/MWh) for a specified region.
        Omitting the starttime and endtime parameters will return the most recently generated forecast.
        Use the starttime and endtime parameters to obtain historical forecast data.

        TODO: If start to end time range is > 24 hours, automatically break up into multiple requests
        Args:
            balancing_auth (str): Balancing authority abbreviation. Example: 'CAISO_NORTH'
            starttime (_type_, optional): Used to generate forcast between start and endtime. Format as "YYYY-MM-DDT-HH:MM:SS-%Z". Defaults to None.
            endtime (_type_, optional): Used to generate forcast between start and endtime. Format as "YYYY-MM-DDT-HH:MM:SS-%Z". Defaults to None.
            extended_forecast (bool, optional): Will provide a 72-hour forecast. Defaults to False.

        Returns:
            dict: Forecast of the MOERs (e.g. CO2 lbs/MWh) for a specified region.
        """
        params = {"ba": balancing_auth}
        if starttime:
            params["starttime"] = starttime
        if endtime:
            params["endtime"] = endtime
        if extended_forecast:
            params["extended_forecast"] = extended_forecast
        try:
            endpoint = self._host + "/forecast"
            self._api_helper()
            r = self._session.get(endpoint, params=params)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            raise Exception(r.json())

    def get_region_map_geometry(self) -> dict:
        """Grid Region Map Geometry
        https://www.watttime.org/api-documentation/#grid-region-map-geometry
        Restricted to customers with ANALYST or PRO subscriptions
        

        Provides a geojson of the grid region boundary for all regions that WattTime covers globally.

        Returns:
            dict: A geojson response, that is a Feature Collection with properties that describe each BA,
                and multipolygon geometry made up of coordinates which define the boundary for each BA.
        """
        try:
            endpoint = self._host + "/maps"
            self._api_helper()
            r = self._session.get(endpoint)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            raise Exception(r.json())
