"""
generic
=======
"""

__all__ = ("GenericModule",)

from ..core.client import Client
from ..utils import Base, BakalibError


class GenericModule(Base):
    """Generic module class, used by other modules.
        
        :param client: Instance of Client, defaults to None
        :type client: Client, optional
        :param url: URL of the school server, defaults to None
        :type url: str, optional
        :param token: Token of the client, defaults to None
        :type token: str, optional
        :raises BakalibError: If Client not logged in
        :raises BakalibError: If invalid module arguments
    """

    url: str
    token: str

    def __init__(
        self, client: Client = None, url: str = None, token: str = None
    ) -> None:
        """Constructor method
        """
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
