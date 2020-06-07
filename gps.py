from typing import List
from dataclasses import dataclass
from datetime import datetime as dt
import math
from loguru import logger


@dataclass()
class Location(object):
    lat: float = 0.0
    lng: float = 0.0
    ns: str = ''
    ew: str = ''
    sog: float = 0.0
    hdg: float = 0.0
    at: str = ''
    valid: bool = False


class GPS(object):
    def __init__(self):

        self.location = Location()
        self.isValid: bool = True
        self.counter: int = 0

        self.dateformat: str = '%Y-%m-%d %H:%M:%S.%f'

    def dm2deg(self, *, dm: float) -> float:  # GPRMC -> GoogleMaps

        decimal, integer = math.modf(dm / 100.0)
        value = integer + ((decimal / 60.0) * 100.0)

        return value

    def convertLatLng(self, *, src: float) -> float:

        decimal, integer = math.modf(src / 100.0)
        value = integer + ((decimal / 60.0) * 100.0)

        return value

    def get(self, *, item: List[bytes]) -> Location:
        try:
            suffix = item[0][2:5]
        except (IndexError,) as e:
            logger.error(e)
        else:
            if suffix == b'RMC':
                self.location.valid = True if item[2] == b'A' else False
                self.location.lat = self.convertLatLng(src=float(item[3])) if item[3] else 0.0
                self.location.ns = item[4].decode() if item[4] else ''
                self.location.lng = self.convertLatLng(src=float(item[5])) if item[5] else 0.0
                self.location.ew = item[6].decode() if item[6] else ''
                self.location.sog = float(item[7]) if item[7] else 0.0
                self.location.hdg = float(item[8]) if item[8] else 0.0
                self.location.at = dt.now().strftime(self.dateformat)
                self.counter += 1

                if self.isValid:
                    if self.location.valid == False:
                        logger.error('--- GPS down')
                else:
                    if self.location.valid == True:
                        logger.debug('*** GPS UP')

                self.isValid = self.location.valid

        return self.location
