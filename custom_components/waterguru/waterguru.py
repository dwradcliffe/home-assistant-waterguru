import logging

from aiohttp import ClientSession
import boto3
import botocore
import requests
from requests_aws4auth import AWS4Auth
from warrant import Cognito
from warrant.aws_srp import AWSSRP

_LOGGER = logging.getLogger(__name__)

class WaterGuruApiError(Exception):
    """Raised when an error occurs while accessing the WaterGuru API."""

class WaterGuru:
    """WaterGuru API wrapper."""

    def __init__(self, username: str, password: str, session: ClientSession):
        """Initialize the API wrapper."""
        self._username = username
        self._password = password
        self._session = session

    def get(self):
        """Get the latest data from the WaterGuru API."""

        _LOGGER.info("Fetching data from WaterGuru API...")

        region_name = "us-west-2"
        pool_id = "us-west-2_icsnuWQWw"
        identity_pool_id = "us-west-2:691e3287-5776-40f2-a502-759de65a8f1c"
        client_id = "7pk5du7fitqb419oabb3r92lni"
        idp_pool = "cognito-idp.us-west-2.amazonaws.com/" + pool_id

        boto3.setup_default_session(region_name = region_name)
        client = boto3.client('cognito-idp', region_name=region_name)
        aws = AWSSRP(username=self._username, password=self._password, pool_id=pool_id, client_id=client_id, client=client)
        try:
            tokens = aws.authenticate_user()
        except botocore.exceptions.ClientError as e:
            raise WaterGuruApiError(e) from e

        id_token = tokens['AuthenticationResult']['IdToken']
        refresh_token = tokens['AuthenticationResult']['RefreshToken']
        access_token = tokens['AuthenticationResult']['AccessToken']
        token_type = tokens['AuthenticationResult']['TokenType']

        u=Cognito(pool_id,client_id,id_token=id_token,refresh_token=refresh_token,access_token=access_token)
        user = u.get_user()
        userId = user._metadata['username']

        boto3.setup_default_session(region_name = region_name)
        identity_client = boto3.client('cognito-identity', region_name=region_name)
        identity_response = identity_client.get_id(IdentityPoolId=identity_pool_id)
        identity_id = identity_response['IdentityId']

        credentials_response = identity_client.get_credentials_for_identity(IdentityId=identity_id,Logins={idp_pool:id_token})
        credentials = credentials_response['Credentials']
        access_key_id = credentials['AccessKeyId']
        secret_key = credentials['SecretKey']
        service = 'lambda'
        session_token = credentials['SessionToken']
        expiration = credentials['Expiration']

        method = 'POST'
        headers = {'User-Agent': 'aws-sdk-iOS/2.24.3 iOS/14.7.1 en_US invoker', 'Content-Type': 'application/x-amz-json-1.0'}
        body = {"userId":userId, "clientType":"WEB_APP", "clientVersion":"0.2.3"}
        service = 'lambda'
        url = 'https://lambda.us-west-2.amazonaws.com/2015-03-31/functions/prod-getDashboardView/invocations'
        region = 'us-west-2'

        auth = AWS4Auth(access_key_id, secret_key, region, service, session_token=session_token)
        response = requests.request(method, url, auth=auth, json=body, headers=headers)

        data = response.json()
        return {waterBodyData['waterBodyId']: WaterGuruDevice(waterBodyData) for waterBodyData in data['waterBodies']}



class WaterGuruDevice:
    """Representation of a WaterGuru device."""

    def __init__(self, waterBodyData):
        """Initialize the device."""
        self._data = waterBodyData
        self._sensors = dict[str, str]
        self._standard_sensors = {
            'temp': self._data['waterTemp'],
            'rssi': self._data['pods'][0]['rssiInfo']['rssi'],
        }
        for r in self._data['pods'][0]['refillables']:
            if r['type'] == 'BATT':
                self._standard_sensors['battery'] = r['pctLeft']
            if r['type'] == 'LAB':
                self._standard_sensors['cassette'] = r['pctLeft']
                if 'timeLeftText' in r:
                    number = int(r['timeLeftText'].split()[0])
                    if "weeks" in r['timeLeftText']:
                        number = number * 7
                    elif "months" in r['timeLeftText']:
                        number = number * 30
                    self._standard_sensors['cassette_days_remaining'] = number
        self._measurements = {measurement['type']: measurement for measurement in self._data['measurements']}

    @property
    def device_id(self):
        """Return the device ID."""
        return self._data['waterBodyId']

    @property
    def name(self):
        """Return the name of the device."""
        return f"WaterGuru {self._data['name']}"

    @property
    def product_name(self):
        """Return the product name of the device."""
        return self._data['pods'][0]['pod']['product']

    @property
    def serial_number(self):
        """Return the serial number of the device."""
        return self._data['pods'][0]['pod']['podId']

    @property
    def firmware_version(self):
        """Return the firmware version of the device."""
        return self._data['pods'][0]['pod']['fwUpdateVersion']

    @property
    def sensors(self):
        """Return the sensors of the device."""
        return self._standard_sensors

    @property
    def measurements(self):
        """Return the measurements of the device."""
        return self._measurements

    @property
    def status(self):
        """Return the status of the device."""
        return self._data['status']

    @property
    def last_measurement_time(self):
        """Return the last measurement time."""
        return self._data['latestMeasureTime']

    @property
    def diagnostics(self):
        """Return the diagnostics of the device."""
        return {
            "name": self.name,
            "product_name": self.product_name,
            "firmware_version": self.firmware_version,
            "status": self.status,
            "last_measurement_time": self.last_measurement_time,
            "standard_sensors": self.sensors,
            "measurements": self.measurements,
            "raw_data": self._data
        }
