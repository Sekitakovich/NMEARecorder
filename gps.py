from typing import List
from dataclasses import dataclass
from datetime import datetime as dt
import math
from loguru import logger


@dataclass()
class Location(object):
    lat: float = 0.0
    lng: float = 0.0
    sog: float = 0.0
    hdg: float = 0.0
    at: dt = dt.now()


class GPS(object):
    def __init__(self):

        self.location = Location()
        self.counter: int = 0

    def convertLatLng(self, *, src: float) -> float:
        val = math.modf(src / 100)
        return val[1] + val[0] / 60

    def get(self, *, item: List[bytes]) -> Location:
        try:
            suffix = item[0][2:5]
        except (IndexError,) as e:
            logger.error(e)
        else:
            if suffix == b'RMC':
                if item[2] == b'A':
                    self.location.lat = self.convertLatLng(src=float(item[3])) if item[3] else 0.0
                    self.location.lng = self.convertLatLng(src=float(item[5])) if item[5] else 0.0
                    self.location.sog = float(item[7]) if item[7] else 0.0
                    self.location.hdg = float(item[8]) if item[8] else 0.0
                    self.location.at = dt.now()
                    self.counter += 1
                else:
                    logger.error('Not valid')
        return self.location
