from typing import List
from datetime import datetime as dt
from dataclasses import dataclass

@dataclass()
class SerialPort(object):
    name: str
    baudrate: int


