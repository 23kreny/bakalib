"""
util
====
"""

__all__ = ("BakalibError", "Base", "cache", "_setup_logger")

import datetime as _datetime
import inspect as _inspect
import logging as _logging
import pathlib as _pathlib
import sys as _sys

import cachetools as _cachetools
import requests as _requests
import xmltodict as _xmltodict

_log_dir = _pathlib.Path(_pathlib.Path.home() / ".bakalib")
_log_file = _pathlib.Path(
    _log_dir / (_datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".log")
)


if not _log_dir.is_dir():
    _log_dir.mkdir()
else:
    _logs = [f for f in _log_dir.iterdir()]
    _logs.sort()
    while len(_logs) > 5:
        _logs[0].unlink()
        _logs.pop(0)

_log_file.touch()


def _setup_logger(name: str) -> _logging.Logger:
    """Sets up a logger with the provided name
    
    :param name: Name of the logger
    :type name: str
    :return: Ready-to-use logger
    :rtype: _logging.Logger
    """
    formatter = _logging.Formatter(
        fmt="%(asctime)s — %(name)s — %(levelname)s — %(message)s — %(funcName)s:%(lineno)d"
    )
    handler = _logging.FileHandler(_log_file, mode="a")
    handler.setFormatter(formatter)
    logger = _logging.getLogger(name)
    logger.setLevel(_logging.DEBUG)
    logger.addHandler(handler)
    return logger


_logger = _setup_logger("default")

cache = _cachetools.LFUCache(32)


class BakalibError(Exception):
    """:class:`Exception` subclass, used for differentiating between Python exceptions and bakalib exceptions
    """

    pass


class Base:
    """Base class for most of the classes present in this library
    """

    @_cachetools.cached(cache)
    def request(self, **kwargs: str) -> dict:
        """Generic request method
        
        :param gethx: Name of the client
        :type gethx: str, optional
        :param hx: Access token
        :type hx: str, optional
        :param pm: Module name
        :type pm: str, optional
        :param pmd: Module arguments
        :type pmd: str, optional
        :raises BakalibError: If received response is invalid
        :return: Received response
        :rtype: dict
        """
        resp = _requests.get(url=self.url, params=kwargs, verify=False)
        results: dict = _xmltodict.parse(resp.content).get("results")

        try:
            res: dict = results.get("res")
            result: dict = results.get("result")
        except AttributeError as e:
            log_args: dict = kwargs.copy()
            log_args.pop(k="hx", d=None)
            log_args.pop(k="gethx", d=None)
            _logger.error(log_args)

        comp: str = res if res else result

        if not comp == "01":
            raise BakalibError("Received response is invalid")

        return results
