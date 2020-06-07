import time
from datetime import datetime as dt
from typing import List
from contextlib import closing
import pathlib
import sqlite3
from multiprocessing import Process, Queue as MPQueue, Lock
from queue import Queue, Empty
from dataclasses import dataclass
from loguru import logger


@dataclass()
class Record(object):
    sentence: bytes = b''  # NMEA asis
    # passed: float  # delta secs from prev
    at: dt = dt.now()  # 受信日時


class DBSession(Process):
    def __init__(self, *, path: str, timeout: int = 5, buffersize: int = 32):
        super().__init__()
        self.daemon = True
        self.name = 'SQLite'

        self.qp: MPQueue = MPQueue()
        self.path = pathlib.Path(path)  # path for *.db
        self.nameformat: str = '%04d-%02d-%02d.db'
        self.dateformat: str = '%Y-%m-%d %H:%M:%S.%f'
        self.locker = Lock()

        self.counter: int = 0
        now = dt.now()
        self.lastat: dt = now
        self.lastsave: dt = now
        self.timeout = timeout
        # self.buffer: List[Record] = []
        self.buffersize = buffersize

        self.fifo = Queue()

        self.schema = 'CREATE TABLE "sentence" ( \
                    	"id"	INTEGER NOT NULL DEFAULT 0 PRIMARY KEY AUTOINCREMENT, \
                        "at"	TEXT NOT NULL DEFAULT \'\', \
                        "ds"	REAL NOT NULL DEFAULT 0.0, \
                        "nmea"	TEXT NOT NULL DEFAULT \'\' \
                    )'

    def __del__(self):
        self.append(at=self.lastat)

    def create(self, *, cursor: sqlite3.Cursor):
        cursor.execute(self.schema)

    def append(self, *, at: dt):
        size = self.fifo.qsize()
        if size:
            passed = (at - self.lastat).total_seconds()
            name = self.nameformat % (at.year, at.month, at.day)
            file = self.path / name  # pathlib
            exists = file.exists()
            now = dt.now()
            with closing(sqlite3.connect(str(file))) as db:
                ts = time.time()
                cursor = db.cursor()
                if exists is False:
                    self.create(cursor=cursor)
                for index in range(size):
                    ooo: Record = self.fifo.get()
                    item = [ooo.at.strftime(self.dateformat), passed, ooo.sentence]
                    # print(item)
                    query = 'insert into sentence(at,ds,nmea) values(?,?,?)'
                    cursor.execute(query, item)
                cursor.close()
                db.commit()  # never forget
                te = time.time()
                after = int((now - self.lastsave).total_seconds())
                logger.debug(
                    '+++ %d records were saved to %s in %f after %d secs' % (size, file, round(te - ts, 2), after))
                self.lastsave = now

    # def _append(self, *, at: dt):
    #     # logger.debug(self.fifo.qsize())
    #     with self.locker:  # 念の為
    #         rows = self.buffer.copy()
    #         self.buffer.clear()
    #         passed = (at - self.lastat).total_seconds()
    #         name = self.nameformat % (at.year, at.month, at.day)
    #         file = self.path / name  # pathlib
    #         exists = file.exists()
    #         now = dt.now()
    #         with closing(sqlite3.connect(str(file))) as db:
    #             ts = time.time()
    #             cursor = db.cursor()
    #             if exists is False:
    #                 self.create(cursor=cursor)
    #             for ooo in rows:
    #                 item = [ooo.at.strftime(self.dateformat), passed, ooo.sentence]
    #                 query = 'insert into sentence(at,ds,nmea) values(?,?,?)'
    #                 print(item)
    #                 cursor.execute(query, item)
    #             cursor.close()
    #             db.commit()  # never forget
    #             te = time.time()
    #             after = int((now - self.lastsave).total_seconds())
    #             logger.debug(
    #                 '+++ %d records were saved to %s in %f after %d secs' % (len(rows), file, round(te - ts, 2), after))
    #             self.lastsave = now
    #
    def run(self) -> None:
        logger.debug('DBSession start (%d)' % self.pid)
        while True:
            try:
                raw: bytes = self.qp.get(timeout=self.timeout)
                self.counter += 1
            except Empty as e:
                self.append(at=self.lastat)
                self.lastat = dt.now()
            except KeyboardInterrupt as e:
                self.append(at=self.lastat)
                break
            else:
                now = dt.now()
                if now.day != self.lastat.day:
                    self.append(at=self.lastat)
                    logger.debug('just in today')

                record = Record(sentence=raw, at=now)
                self.fifo.put(record)

                if self.fifo.qsize() >= self.buffersize:
                    self.append(at=now)

                self.lastat = now
