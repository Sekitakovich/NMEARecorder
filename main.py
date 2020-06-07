import argparse
import time
from typing import Dict
from loguru import logger
import pathlib
from multiprocessing import Queue
import responder
from threading import Thread
import os
from dataclasses import dataclass, asdict
import json
from functools import reduce
from operator import xor
from datetime import datetime as dt

from receiver import Receiver
from dbsession import DBSession
from mc import fromUDP
from websocketServer import WebsocketServer
from gps import GPS
from patrol import Patrol


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
        self.g = GPS()
        self.ws = WebsocketServer(debug=True)

        self.qp = Queue()

        self.dbsession = DBSession(path=pathlib.Path(path), buffersize=bs, timeout=to)
        self.dbsession.start()
        self.process[self.dbsession.name] = self.dbsession.pid
        self.ppp[self.dbsession.name] = Patrol(pid=self.dbsession.pid)

        self.receiver = Receiver(port=port, baudrate=baudrate, qp=self.qp)
        self.receiver.start()
        self.process[self.receiver.name] = self.receiver.pid
        self.ppp[self.receiver.name] = Patrol(pid=self.receiver.pid)

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

        self.add_route('/ws', self.ws.wsserver, websocket=True)
        self.add_route('/', self.top)
        self.add_route('/main.js', self.mainJS)
        self.add_route('/classes.js', self.classes)

        self.add_event_handler('shutdown', self.cleanup)
        self.run(address='0.0.0.0', port=http)

    async def cleanup(self):
        self.dbsession.join()
        self.receiver.join()
        self.mc.join()
        logger.debug('... OK! shutdown')

    def top(self, req: responder.Request, resp: responder.Response):
        resp.content = self.template('index.html')

    def classes(self, req: responder.Request, resp: responder.Response):
        resp.content = self.template('classes.js')

    def mainJS(self, req: responder.Request, resp: responder.Response):
        resp.content = self.template('main.js')

    def collector(self):
        loop: bool = True
        try:
            while loop:
                try:
                    raw: bytes = self.receiver.qp.get()
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
                                    ooo = {'type': 'location', 'info': asdict(location)}
                                    self.ws.broadcast(message=json.dumps(ooo))
                                    if location.valid:
                                        print(location)

        except KeyboardInterrupt as e:
            loop = False

    def patrol(self):
        loop: bool = True
        try:
            while loop:
                time.sleep(5)
                stats = {'type': 'stats', 'info': {}}
                # logger.info('--------------------------------------------------------------------')
                for k, v in self.ppp.items():
                    stats['info'][k] = asdict(v.stats)

                # logger.info(stats)
                self.ws.broadcast(message='%s' % json.dumps(stats, indent=2))
        except KeyboardInterrupt as e:
            loop = False


if __name__ == '__main__':

    portDefault: str = '/dev/ttyACM0:9600'
    toDefault: int = 5
    bsDefault: int = 2500

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
