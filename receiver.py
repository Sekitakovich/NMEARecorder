import serial
from threading import Thread, Lock
from queue import Queue
from loguru import logger


class Receiver(Thread):

    def __init__(self, *, port: str, baudrate: int):

        super().__init__()
        self.daemon = True

        self.port = port
        self.baudrate = baudrate

        self.isReady = False
        self.qp = Queue()
        try:
            self.sp = serial.Serial(port=port, baudrate=baudrate)
        except (OSError,) as e:
            logger.error(e)
        else:
            self.isReady = True

    def run(self) -> None:
        try:
            while self.isReady:
                data = self.sp.readline()
                self.qp.put(data)
        except (serial.SerialException, OSError) as e:
            self.isReady = False
            logger.error(e)

    def __del__(self):
        if self.isReady:
            self.sp.close()
            logger.info('%s was closed' % self.port)


