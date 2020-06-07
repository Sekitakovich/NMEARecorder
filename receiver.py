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

    def run(self) -> None:
        logger.debug('Receiver start (%d)' % self.pid)
        while self.isReady:
            try:
                data = self.sp.readline()
            except (serial.SerialException, OSError) as e:
                self.isReady = False
                logger.error(e)
            except KeyboardInterrupt as e:
                self.isReady = False
            else:
                self.qp.put(data)

        self.sp.close()
        logger.debug('<<< Roger!')

    def __del__(self):
        if self.isReady:
            self.sp.close()
            logger.info('%s was closed' % self.port)


