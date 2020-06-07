import serial
from loguru import logger
from multiprocessing import Process, Queue


class Receiver(Process):

    def __init__(self, *, port: str, baudrate: int, qp: Queue):

        super().__init__()
        self.daemon = True
        self.name = 'Serial'

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

    # def cook(self, *, data: bytes):
    #     part = data.split(b'*')
    #     main = part[0][1:]
    #     if len(part) > 1:
    #         csum = int(part[1][:2], 16)
    #         calc = reduce(xor, main, 0)
    #         if calc != csum:
    #             logger.error('!!! bad checksum')

    def run(self) -> None:
        logger.debug('Receiver start (%d)' % self.pid)
        try:
            while self.isReady:
                data = self.sp.readline()
                self.qp.put(data)
                # self.cook(data=data)
        except (serial.SerialException, OSError) as e:
            self.isReady = False
            logger.error(e)
        except KeyboardInterrupt as e:
            self.isReady = False

    def __del__(self):
        if self.isReady:
            self.sp.close()
            logger.info('%s was closed' % self.port)


