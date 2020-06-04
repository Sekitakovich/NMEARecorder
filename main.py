import argparse
import serial
from typing import List
from dataclasses import dataclass
from datetime import datetime as dt
from multiprocessing import Process, Queue


@dataclass()
class SerialPort(object):

    name: str
    baudrate: int


class Receiver(Process):

    def __init__(self, *, port: str, baudrate: int, qp: Queue):

        super().__init__()

        self.daemon = True
        self.isReady: bool = False
        self.qp: Queue = qp

        try:
            sp = serial.Serial(port=port, baudrate=baudrate)
        except serial.SerialException as e:
            print(e)
        else:
            self.isReady = True
            self.sp = sp

    def run(self) -> None:
        while True:
            data = self.sp.readline()
            self.qp.put(data)

    def __del__(self):
        if self.sp:
            self.sp.close()


class Main(object):

    def __init__(self, *, port: List[SerialPort]):

        self.device: List[Process] = []
        self.counter: int = 0
        self.qp: Queue = Queue()

        now = dt.now()
        self.dbPath = 'db'
        self.dbfile: str = '%s/%04d-%02d-%02d-%02d-%02d-%02d.db' % \
                           (self.dbPath,
                            now.year, now.month, now.day,
                            now.hour, now.minute, now.second)

        for s in port:
            t = Receiver(port=s.name, baudrate=s.baudrate, qp=self.qp)
            if t.isReady:
                t.start()
                self.device.append(t)
            else:
                pass

        print(self.device)
        while True:
            try:
                raw: bytes = self.qp.get()
            except (KeyboardInterrupt, serial.SerialException) as e:
                print(e)
                break
            else:
                now = dt.now()
                nmea = raw.decode()
                print('at %s: %s' % (now, raw))
                self.counter += 1


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
        print(e)
    else:
        print(port)
        if len(port):
            main = Main(port=port)
