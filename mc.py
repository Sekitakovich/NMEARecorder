from contextlib import closing
import socket
from multiprocessing import Process, Queue
from functools import reduce
from operator import xor
from loguru import logger


class fromUDP(Process):
    def __init__(self, *, mcip: str, mcport: int, quePoint: Queue):
        super().__init__()
        self.daemon = True
        self.name = 'Multicast'

        self.mcip = mcip
        self.mcport = mcport
        self.quePoint = quePoint

    # def cook(self, *, data: bytes):
    #     part = data.split(b'*')
    #     main = part[0][1:]
    #     if len(part) > 1:
    #         csum = int(part[1][:2], 16)
    #         calc = reduce(xor, main, 0)
    #         if calc != csum:
    #             logger.error('!!! bad checksum')

    def run(self) -> None:
        logger.debug('fromUDP (%d)' % self.pid)
        bufferSize = 4096
        run = True
        try:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                                socket.inet_aton(self.mcip) + socket.inet_aton('0.0.0.0'))
                sock.bind(('', self.mcport))

                while run:
                    udpPacket, ipv4 = sock.recvfrom(bufferSize)
                    self.quePoint.put(udpPacket)
                    # self.cook(data=udpPacket)
        except (socket.error, KeyboardInterrupt) as e:
            run = False
            logger.critical(e)
