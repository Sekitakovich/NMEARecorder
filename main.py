import argparse
import serial
from typing import List
from datetime import datetime as dt
from multiprocessing import Queue as MPQueue
from threading import Thread, Lock
from queue import Queue
from loguru import logger
import pathlib

from common import SerialPort, Record
from dbsession import DBSession


class Receiver(Thread):

    def __init__(self, *, port: str, baudrate: int, qp: Queue):

        super().__init__()
        self.daemon = True

        self.port = port
        self.baudrate = baudrate

        self.isReady = False
        self.qp = qp
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


class Main(object):

    def __init__(self, *, port: List[SerialPort], path: str = 'db'):

        self.ready: bool = True
        self.locker = Lock()
        now = dt.now()

        self.device: List[Thread] = []

        self.timeout: int = 5
        self.qp: Queue = Queue()

        self.saveQueue = MPQueue()
        self.dbsession = DBSession(qp=self.saveQueue, path=pathlib.Path(path))
        self.dbsession.start()

        for s in port:
            t = Receiver(port=s.name, baudrate=s.baudrate, qp=self.qp)
            try:
                t.start()
            except Exception as e:
                logger.error(e)
            else:
                if t.isReady:
                    self.device.append(t)
                else:
                    self.ready = False
                    break

    def start(self):
        while True:
            try:
                raw: bytes = self.qp.get()
            except (KeyboardInterrupt,) as e:
                break
            else:
                self.saveQueue.put(raw)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help='name:baudrate of port', default='com8:9600')

    args = parser.parse_args()

    port: List[SerialPort] = []

    try:
        for src in args.port.split(','):
            ooo: str = src.split(':')
            name: str = ooo[0]
            baudrate: int = int(ooo[1])
            port.append(SerialPort(name=name, baudrate=baudrate))
    except (IndexError, ValueError) as e:
        logger.error(e)
    else:
        if len(port):
            main = Main(port=port)
            if main.ready:
                main.start()
