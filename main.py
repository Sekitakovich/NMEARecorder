import argparse
import time
from typing import Dict
from loguru import logger
import pathlib
from multiprocessing import Queue
import responder
from threading import Thread
import os
import psutil
from dataclasses import dataclass, asdict
import json
from functools import reduce
from operator import xor

from receiver import Receiver
from dbsession import DBSession
from mc import fromUDP
from websocketServer import WebsocketServer
from gps import GPS


@dataclass()
class Stats(object):
    cpuPercent: float = 0.0
    memPercent: float = 0.0


class Patrol(Thread):
    def __init__(self, *, pid: int, interval: float = 5):
        super().__init__()
        self.daemon = True
        self.p = psutil.Process(pid=pid)
        self.interval = interval

        self.stats = Stats()

    def run(self) -> None:
        while True:
            self.stats.cpuPercent = self.p.cpu_percent(interval=self.interval / 2)
            self.stats.memPercent = self.p.memory_percent()
            time.sleep(self.interval)


class Main(responder.API):

    def __init__(self, *, port: str, baudrate: int, path: str = 'db', bs: int = 32, to: int = 5, http: int = 8080):

        super().__init__()
        pid = os.getpid()
        self.process: Dict[str, int] = {}
        self.process['main'] = pid
        self.ppp: Dict[str, Patrol] = {}
        self.ppp['main'] = Patrol(pid=pid)

        logger.info('*** NMEA Recorder startup (%d)' % pid)

        self.ready: bool = True
        self.qp = Queue()

        self.dbsession = DBSession(path=pathlib.Path(path), buffersize=bs, timeout=to)
        self.dbsession.start()
        self.process[self.dbsession.name] = self.dbsession.pid
        self.ppp[self.dbsession.name] = Patrol(pid=self.dbsession.pid)

        self.t = Receiver(port=port, baudrate=baudrate, qp=self.qp)
        self.t.start()
        self.process[self.t.name] = self.t.pid
        self.ppp[self.t.name] = Patrol(pid=self.t.pid)

        self.mc = fromUDP(quePoint=self.qp, mcip='239.192.0.1', mcport=60001)
        self.mc.start()
        self.process[self.mc.name] = self.mc.pid
        self.ppp[self.mc.name] = Patrol(pid=self.mc.pid)

        self.main = Thread(target=self.collector, name='MainLoop', daemon=True)
        self.main.start()

        self.p = Thread(target=self.patrol, name='Patrol', daemon=True)
        self.p.start()
        for k, v in self.ppp.items():
            v.start()

        self.g = GPS()

        self.ws = WebsocketServer(debug=True)
        self.add_route('/ws', self.ws.wsserver, websocket=True)

        self.run(address='0.0.0.0', port=http)

    def collector(self):
        loop: bool = True
        try:
            while loop:
                try:
                    raw: bytes = self.t.qp.get()
                except (KeyboardInterrupt,) as e:
                    break
                else:
                    self.dbsession.qp.put(raw)

                    part = raw.split(b'*')
                    if len(part) > 1:
                        main = part[0][1:]
                        csum = int(part[1][:2], 16)
                        calc = reduce(xor, main, 0)
                        if calc != csum:
                            logger.error('!!! bad checksum')
                        else:
                            item = main.split(b',')
                            symbol = item[0]
                            prefix = symbol[0:2]
                            suffix = symbol[2:5]
                            if prefix == b'GP':
                                if suffix == b'RMC':
                                    location = self.g.get(item=item)
                                    print(location)

        except KeyboardInterrupt as e:
            loop = False

    def patrol(self):
        loop: bool = True
        try:
            while loop:
                time.sleep(5)
                stats = {'type': 'stats', 'info': {}}
                logger.info('--------------------------------------------------------------------')
                for k, v in self.ppp.items():
                    logger.info('%s: %s' % (k, v.stats))
                    stats['info'][k] = asdict(v.stats)

                self.ws.bc(message='%s' % json.dumps(stats, indent=2))
        except KeyboardInterrupt as e:
            loop = False


if __name__ == '__main__':

    portDefault: str = '/dev/ttyACM0:9600'
    toDefault: int = 5
    bsDefault: int = 32

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help='name:baudrate of port', default=portDefault)
    parser.add_argument('-b', '--buffersize', help='buffersize', type=int, default=bsDefault)
    parser.add_argument('-t', '--timeout', help='timeout secs', type=int, default=toDefault)

    args = parser.parse_args()

    port = args.port
    to = args.timeout
    bs = args.buffersize

    try:
        ooo: str = port.split(':')
        name: str = ooo[0]
        baudrate: int = int(ooo[1])
    except (IndexError, ValueError) as e:
        logger.error(e)
    else:
        main = Main(port=name, baudrate=baudrate, to=to, bs=bs)
