import argparse
import serial
from typing import List
from dataclasses import dataclass
from datetime import datetime as dt
from multiprocessing import Process, Queue as MPQueue
from threading import Thread, Lock
from queue import Queue, Empty
from contextlib import closing
from loguru import logger


@dataclass()
class SerialPort(object):
    name: str
    baudrate: int


@dataclass()
class Record(object):
    sentence: bytes  # NMEA asis
    passed: float  # delta secs from prev
    at: dt  # 受信日時


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


class DBSession(Process):
    def __init__(self, *, qp: MPQueue):
        super().__init__()
        self.daemon = True
        self.qp = qp

    def run(self) -> None:
        while True:
            rows: List[Record] = self.qp.get()
            now = dt.now()
            dbPath = 'db'
            dbfile: str = '%s/%04d-%02d-%02d.db' % \
                          (dbPath,
                           now.year, now.month, now.day)
            print(rows)


class Main(object):

    def __init__(self, *, port: List[SerialPort]):

        self.ready: bool = True
        self.locker = Lock()
        now = dt.now()

        self.device: List[Thread] = []

        self.counter: int = 0
        self.lastat: dt = now
        self.timeout: int = 5
        self.qp: Queue = Queue()
        self.buffer: List[Record] = []
        self.full: int = 64
        self.lastsave: dt = now

        self.saveQueue = MPQueue()
        self.dbsession = DBSession(qp=self.saveQueue)
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

    def save(self):
        if len(self.buffer):
            with self.locker:
                now = dt.now()
                rows = self.buffer.copy()
                self.saveQueue.put(rows)
                logger.debug('+++ saved %d rows after %f' % (len(rows), (now-self.lastsave).total_seconds()))
                self.buffer.clear()
                self.lastsave = now

    def start(self):
        while True:
            try:
                raw: bytes = self.qp.get(timeout=self.timeout)
            except Empty as e:
                # logger.debug('Timeout')
                self.save()
            except (KeyboardInterrupt,) as e:
                self.save()
                logger.error(e)
                break
            else:
                now = dt.now()
                record = Record(sentence=raw, at=now, passed=(now - self.lastat).total_seconds())

                with self.locker:
                    self.buffer.append(record)
                if len(self.buffer) == self.full:
                    # logger.debug('Full')
                    self.save()

                # print(record)
                self.counter += 1
                self.lastat = now


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
