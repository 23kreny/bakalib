"""
municipality
============
"""

__all__ = ("Municipality",)

import dataclasses
from typing import List

import requests
import xmltodict
from cachetools import cached

from ..utils import BakalibError, _setup_logger, cache


class Municipality:
    """This is a container for certain methods for fetching cities and schools using Bakaláři school system
    
    :raises RuntimeError: If the class gets instantiated
    """

    municipality_url = "https://sluzby.bakalari.cz/api/v1/municipality/"
    logger = _setup_logger("[MUNICIPALITY]")

    @dataclasses.dataclass(frozen=True)
    class City:
        name: str
        school_count: int

    @dataclasses.dataclass(frozen=True)
    class School:
        id: str
        name: str
        url: str

    def __new__(cls, *args, **kwargs):
        raise RuntimeError(f"{cls} should not be instantiated!")

    @classmethod
    @cached(cache)
    def cities(cls) -> List["Municipality.City"]:
        """Fetches all cities in municipality database
        
        :raises BakalibError: If fails to retrieve cities
        :return: List of cities
        :rtype: List[Municipality.City]
        """
        try:
            resp = requests.get(cls.municipality_url, stream=True)
            parsed = xmltodict.parse(resp.content)
            return [
                cls.City(city["name"], int(city["schoolCount"]))
                for city in parsed["ArrayOfmunicipalityInfo"]["municipalityInfo"]
                if city["name"]
            ]
        except Exception as e:
            cls.logger.error(f"{type(e)}: {e}")
            raise BakalibError("Failed to retrieve city list from municipality")

    @classmethod
    def schools(cls, city: str) -> List["Municipality.School"]:
        """Fetches all schools in a specified city
        
        :param city: Name of a city
        :type city: str
        :raises BakalibError: If city not found
        :raises BakalibError: If failed to retrieve schools
        :return: List of schools
        :rtype: List[Municipality.School]
        """
        try:
            city_url = f"{cls.municipality_url}{city}"
            resp = requests.get(requests.utils.requote_uri(city_url), stream=True)

            if resp.status_code == 404:
                raise BakalibError("City not found")

            parsed = xmltodict.parse(resp.content)
            schools = parsed["municipality"]["schools"]["schoolInfo"]
            schools = schools if isinstance(schools, list) else [schools]

            return [
                cls.School(school["id"], school["name"], school["schoolUrl"])
                for school in schools
                if school["name"]
            ]
        except Exception as e:
            cls.logger.error(f"{type(e)}: {e}")
            raise BakalibError("Failed to retrieve school list from municipality")
