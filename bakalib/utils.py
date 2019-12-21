"""
util
====
"""

__all__ = (
    "cache",
    "data_dir",
    "request",
    "BakalibError",
)

import pathlib

import cachetools
import requests
import urllib3
import xmltodict

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

cache = cachetools.TTLCache(32, 300)
data_dir = pathlib.Path(__file__).parent.joinpath("data")


@cachetools.cached(cache)
def request(url: str, **kwargs) -> dict:
    """
    Make a GET request to school URL.\n
    Module names are available at `https://github.com/bakalari-api/bakalari-api/tree/master/moduly`.
    >>> # Valid types of requests
    >>> request("https://example.com/login.aspx", gethx="Username123")
    >>> request("https://example.com/login.aspx", hx="token1234=", pm="module_name", pmd="20191219") # pmd is optional
    """
    if not kwargs or len(kwargs) > 3:
        raise BakalibError("Bad arguments")

    r = requests.get(url=url, params=kwargs, verify=False)
    response = xmltodict.parse(r.content)
    results = response.get("results")

    try:
        res = results.get("res")
        result = results.get("result")
    except AttributeError as e:
        pass

    comp = res if res else result

    if not comp == "01":
        raise BakalibError("Received response is invalid")

    return results


class BakalibError(Exception):
    pass
