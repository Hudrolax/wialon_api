from pprint import pprint
from builtins import str
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
import gzip
import io
from pydantic import BaseModel
from flask import Flask, request

TOKEN = "a61c128839b55d813925bc3ef25945c244D4A67E658AECB68B9BC68C12FC85BACC846D2A"

if __name__ == '__main__':
    app = Flask(__name__)

class WialonError(Exception):
    """
    Exception raised when an Wialon Remote API call fails due to a network
    related error or for a Wialon specific reason.
    """
    errors = {
        1: 'Invalid session',
        2: 'Invalid service',
        3: 'Invalid result',
        4: 'Invalid input',
        5: 'Error performing request',
        6: 'Unknow error',
        7: 'Access denied',
        8: 'Invalid user name or password',
        9: 'Authorization server is unavailable, please try again later',
        1001: 'No message for selected interval',
        1002: 'Item with such unique property already exists',
        1003: 'Only one request of given time is allowed at the moment'
    }

    def __init__(self, code, text):
        self._text = text
        self._code = code
        try:
            self._code = int(code)
        except ValueError:
            pass

    def __unicode__(self):
        explanation = self._text
        if (self._code in WialonError.errors):
            explanation = " ".join([WialonError.errors[self._code], self._text])

        message = u'{error} ({code})'.format(error=explanation, code=self._code)
        return u'WialonError({message})'.format(message=message)

    def __str__(self):
        return self.__unicode__()

    def __repr__(self):
        return str(self)


class Wialon(object):
    request_headers = {
        'Accept-Encoding': 'gzip, deflate'
    }

    def __init__(self, scheme='http', host="hst-api.wialon.com", port=80, sid=None, **extra_params):
        """
        Created the Wialon API object.
        """
        self._sid = sid
        self.__default_params = {}
        self.__default_params.update(extra_params)

        self.__base_url = (
            '{scheme}://{host}:{port}'.format(
                scheme=scheme,
                host=host,
                port=port
            )
        )

        self.__base_api_url = urljoin(self.__base_url, 'wialon/ajax.html?')

    @property
    def sid(self):
        return self._sid

    @sid.setter
    def sid(self, value):
        self._sid = value

    def update_extra_params(self, **params):
        """
        Updated the Wialon API default parameters.
        """
        self.__default_params.update(params)

    def gis_searchintelli(self, phrase, count=1):
        """
        получить координаты по адресу, составленному в произвольной форме
        """
        url = urljoin(self.__base_url, 'gis_searchintelli')
        params = {
            'sid': self.sid,
            'phrase': phrase,
            'count': count,
            'indexFrom': 0,
            'uid': self.uid
        }

        return self.request('gis_searchintelli', url, params)

    def base_url(self):
        return self.__base_url

    def avl_evts(self):
        """
        Call avl_event request
        """
        url = urljoin(self.__base_url, 'avl_evts')
        params = {
            'sid': self.sid
        }

        return self.request('avl_evts', url, params)

    def call(self, action, *argc, **kwargs):
        """
        Call the API method provided with the parameters supplied.
        """

        if (not kwargs):
            # List params for batch
            if isinstance(argc, tuple) and len(argc) == 1:
                params = json.dumps(argc[0], ensure_ascii=False)
            else:
                params = json.dumps(argc, ensure_ascii=False)
        else:
            params = json.dumps(kwargs, ensure_ascii=False)

        params = {
            'svc': action.replace('_', '/', 1),
            'params': params.encode("utf-8"),
            'sid': self.sid
        }

        all_params = self.__default_params.copy()
        all_params.update(params)
        return self.request(action, self.__base_api_url, all_params)

    def token_login(self, *args, **kwargs):
        kwargs['appName'] = 'python-wialon'
        result = self.call('token_login', *args, **kwargs)
        self.sid = result['eid']
        self.uid = result['user']['id']
        return result

    def request(self, action, url, params):
        url_params = urlencode(params)
        data = url_params.encode('utf-8')
        try:
            request = Request(url, data, headers=self.request_headers)
            response = urlopen(request)
            response_content = response.read()
        except HTTPError as e:
            raise WialonError(0, u"HTTP {code}".format(code=e.code))
        except URLError as e:
            raise WialonError(0, str(e))

        response_info = response.info()
        content_type = response_info.get('Content-Type')
        content_encoding = response_info.get('Content-Encoding')

        if content_encoding == 'gzip':
            buffer = io.BytesIO(response_content)
            f = gzip.GzipFile(fileobj=buffer)
            try:
                result = f.read()
            finally:
                f.close()
                buffer.close()
        else:
            result = response_content

        try:
            if content_type == 'application/json':
                result = result.decode('utf-8', errors='ignore')
                result = json.loads(result)
        except ValueError as e:
            raise WialonError(
                0,
                u"Invalid response from Wialon: {0}".format(e),
            )

        if (isinstance(result, dict) and 'error' in result and result['error'] > 0):
            raise WialonError(result['error'], action)

        errors = []
        if isinstance(result, list):
            # Check for batch errors
            for elem in result:
                if (not isinstance(elem, dict)):
                    continue
                if "error" in elem:
                    errors.append("%s (%d)" % (WialonError.errors[elem["error"]], elem["error"]))

        if (errors):
            errors.append(action)
            raise WialonError(0, " ".join(errors))

        return result

    def __getattr__(self, action_name):
        """
        Enable the calling of Wialon API methods through Python method calls
        of the same name.
        """

        def get(self, *args, **kwargs):
            return self.call(action_name, *args, **kwargs)

        return get.__get__(self)


class Address(BaseModel):
    city: str
    country: str
    formatted_path: str
    house: str
    region: str
    street: str
    x: str
    y: str


class Addresses(BaseModel):
    items: list = []

    def load(self, data: list):
        for address in data:
            self.items.append(Address(**address['items'][0]))

    class Config:
        json_dumps = lambda v, default: json.dumps(v, default=default, ensure_ascii=False)

def search_coords_by_phrase(phrase: str) -> Addresses:
    wialon_api = Wialon()
    result_login = wialon_api.token_login(token=TOKEN)
    result = wialon_api.gis_searchintelli(phrase, count=1)
    wialon_api.core_logout()
    addresses = Addresses()
    addresses.load(result)
    return addresses

@app.route('/search', methods=['GET'])
def search_phrase() -> str:
    phrase = request.args.get('phrase')
    result = search_coords_by_phrase(phrase)
    return result.json()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)