import argparse
from typing import List
from threading import Thread, Lock
from loguru import logger
import pathlib

from receiver import Receiver
from dbsession import DBSession, Record


class Main(object):

    def __init__(self, *, port: str, baudrate: int, path: str = 'db'):

        self.ready: bool = True
        self.locker = Lock()

        self.device: List[Thread] = []
        self.timeout: int = 5

        self.dbsession = DBSession(path=pathlib.Path(path), buffersize=32, timeout=60)
        self.dbsession.start()

        self.t = Receiver(port=port, baudrate=baudrate)
        try:
            self.t.start()
        except Exception as e:
            logger.error(e)
        else:
            if self.t.isReady is False:
                self.ready = False

    def start(self):
        logger.info('*** NMEA Recorder startup')
        while True:
            try:
                raw: bytes = self.t.qp.get()
                # print(raw)
            except (KeyboardInterrupt,) as e:
                break
            else:
                self.dbsession.qp.put(raw)


if __name__ == '__main__':

    portDefault: str = 'com8:9600'

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help='name:baudrate of port', default=portDefault)

    args = parser.parse_args()

    port = args.port

    try:
        ooo: str = port.split(':')
        name: str = ooo[0]
        baudrate: int = int(ooo[1])
    except (IndexError, ValueError) as e:
        logger.error(e)
    else:
        main = Main(port=name, baudrate=baudrate)
        if main.ready:
            main.start()
