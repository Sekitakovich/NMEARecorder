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
        with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                            socket.inet_aton(self.mcip) + socket.inet_aton('0.0.0.0'))
            sock.bind(('', self.mcport))
            run = True

            while run:
                try:
                    udpPacket, ipv4 = sock.recvfrom(bufferSize)
                except (socket.error,) as e:
                    run = False
                    logger.error(e)
                except KeyboardInterrupt as e:
                    run = False
                else:
                    self.quePoint.put(udpPacket)

            logger.debug('<<< Roger!')

