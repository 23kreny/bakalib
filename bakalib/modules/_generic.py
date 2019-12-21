"""
generic
=======
"""

__all__ = ("Generic",)

from ..core.client import Client
from ..utils import BakalibError


class Generic:
    """
    Generic module boilerplate, takes either `bakalib.client.Client` object or url and token strings.
    >>> client = Client(username="user123", password="abcdefgh", domain="domain.example.com/bakaweb")
    >>> module = Generic(client=client)
    >>> module = Generic(url="domain.example.com/bakaweb", token="abcdefgh12345678")
    """

    def __init__(
            self, client: Client = None, url: str = None, token: str = None
    ) -> None:
        if client:
            if not client.logged_in:
                raise BakalibError("Client is not logged in.")
            self.url = client.url
            self.token = client.token
        elif url and token:
            self.url = url
            self.token = token
        else:
            raise BakalibError("Invalid module arguments.")
