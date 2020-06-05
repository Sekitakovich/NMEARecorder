from typing import List
from datetime import datetime as dt
from dataclasses import dataclass

@dataclass()
class SerialPort(object):
    name: str
    baudrate: int


@dataclass()
class Record(object):
    sentence: bytes  # NMEA asis
    passed: float  # delta secs from prev
    at: dt  # 受信日時

