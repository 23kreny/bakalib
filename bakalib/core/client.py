"""
client
======
"""

__all__ = ("Client",)

import base64
import datetime
import hashlib
from dataclasses import dataclass
from threading import Thread

from ..utils import BakalibError, request


def _is_logged_in_decorator(invert: bool = False):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if args[0].logged_in ^ invert:
                return func(*args, **kwargs)
            else:
                if invert:
                    raise BakalibError("Client is already logged in.")
                raise BakalibError("Client is not logged in.")

        return wrapper

    return decorator


class Client:
    """
    Creates an instance with access to basic information of the user

    Parameters
    ----------
    username : str
        Client username recognizable by school server.
    domain : str
        School server domain (without 'http(s)', 'login.aspx').

    Attributes
    ----------
    username
    domain
    url : str
        School server URL generated from domain.
    perm_token : str
        Permanent token used for 'Remember password' function.
    token : str
        Token used for accessing the server.


    Methods
    -------
    login(password/perm_token: str = None)
        Logs the user in.
    info()
        Obtains user information (school name, year, ...)
    """

    def __init__(self, username: str, domain: str):
        super().__init__()
        self.username = username
        self.domain = domain
        self.url = f"https://{self.domain}/login.aspx"

        self.perm_token = None
        self.token = None
        self.thread = Thread()

        self.logged_in = False

    @_is_logged_in_decorator(invert=True)
    def login(self, password: str = None, perm_token: str = None, check_valid: bool = True):
        if perm_token:
            self.perm_token = perm_token
            token = self._token(self.perm_token)
        elif password:
            self.perm_token = self._permanent_token(self.username, password)
            token = self._token(self.perm_token)
        else:
            raise BakalibError("Incorrect arguments")

        if check_valid:
            if self._is_token_valid(token):
                self.token = token
            else:
                raise BakalibError("Token is invalid: Invalid password/perm_token")
        else:
            self.token = token

        self.thread = Thread(
            target=request, args=(self.url,), kwargs={"hx": self.token, "pm": "login"}
        )
        self.thread.start()

        self.logged_in = True

    def _permanent_token(self, user: str, password: str) -> str:
        """
        Generates a permanent access token with securely hashed password.
        """
        try:
            res = request(url=self.url, gethx=user)
        except BakalibError as e:
            print(e)
            raise BakalibError("Invalid username")

        salt = res.get("salt")
        ikod = res.get("ikod")
        typ = res.get("typ")
        salted_password = (salt + ikod + typ + password).encode("utf-8")
        hashed_password = base64.b64encode(hashlib.sha512(salted_password).digest())
        perm_token = (
                "*login*" + user + "*pwd*" + hashed_password.decode("utf8") + "*sgn*ANDR"
        )
        return perm_token

    @staticmethod
    def _token(perm_token: str) -> str:
        """
        Generates an access token using current time.
        """
        today = datetime.date.today()
        datecode = "{:04}{:02}{:02}".format(today.year, today.month, today.day)
        token_hash = hashlib.sha512((perm_token + datecode).encode("utf-8")).digest()
        token = base64.urlsafe_b64encode(token_hash).decode("utf-8")
        return token

    def _is_token_valid(self, token: str) -> bool:
        """
        Checks for token validity.
        """
        try:
            request(url=self.url, hx=token, pm="login")
            return True
        except BakalibError:
            return False

    @_is_logged_in_decorator()
    def info(self) -> "Client.info.Result":
        """
        Obtains basic information about the user into a NamedTuple.
        >>> user.info().name
        >>> user.info().class_ # <-- due to class being a reserved keyword.
        >>> user.info().school
        """
        if self.thread.is_alive():
            self.thread.join()

        @dataclass(frozen=True)
        class Result:
            version: str
            name: str
            type_abbr: str
            type: str
            school: str
            school_type: str
            class_: str
            year: str
            modules: str
            newmarkdays: str

        response = request(url=self.url, hx=self.token, pm="login")
        result = Result(
            *[
                response.get(element).get("newmarkdays")
                if element == "params"
                else response.get(element)
                for element in response
                if not element == "result"
            ]
        )
        return result
