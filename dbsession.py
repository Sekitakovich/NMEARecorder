from datetime import datetime as dt
from typing import List
from contextlib import closing
import pathlib
import sqlite3
from multiprocessing import Process, Queue as MPQueue, Lock
from queue import Empty
from loguru import logger

from common import SerialPort, Record


class DBSession(Process):
    def __init__(self, *, path: pathlib.Path, qp: MPQueue):
        super().__init__()
        self.daemon = True

        self.qp = qp
        self.path = path  # path for *.db
        self.nameformat = '%04d-%02d-%02d.db'
        self.dateformat = '%Y-%m-%d %H:%M:%S.%f'
        self.locker = Lock()

        self.counter: int = 0
        self.lastat: dt = dt.now()
        self.timeout: int = 5
        self.buffer: List[Record] = []
        self.full: int = 64

        # try:
        #     with open('./schema.txt', 'rt') as f:
        #         schema = f.read()
        # except OSError as e:
        #     logger.error(e)
        # else:
        #     self.schema = schema
        self.schema = 'CREATE TABLE "sentence" ( \
                    	"id"	INTEGER NOT NULL DEFAULT 0 PRIMARY KEY AUTOINCREMENT, \
                        "at"	TEXT NOT NULL DEFAULT \'\', \
                        "ds"	REAL NOT NULL DEFAULT 0.0, \
                        "nmea"	TEXT NOT NULL DEFAULT \'\' \
                    )'

    def create(self, *, cursor: sqlite3.Cursor):
        cursor.execute(self.schema)

    def save(self, *, at: dt):
        with self.locker:  # 念の為
            rows = self.buffer.copy()
            self.buffer.clear()
            name = self.nameformat % (at.year, at.month, at.day)
            file = self.path / name  # pathlib
            exists = file.exists()
            with closing(sqlite3.connect(str(file))) as db:
                cursor = db.cursor()
                if exists is False:
                    self.create(cursor=cursor)
                for ooo in rows:
                    query = 'insert into sentence(at,ds,nmea) values(?,?,?)'
                    cursor.execute(query, [ooo.at.strftime(self.dateformat), ooo.passed, ooo.sentence])
                logger.info('+++ %d records was saved to %s' % (len(rows), file))
                cursor.close()
                db.commit()  # never forget

    def run(self) -> None:
        while True:
            try:
                raw: bytes = self.qp.get(timeout=self.timeout)
                self.counter += 1
            except Empty as e:
                if len(self.buffer):
                    self.save(at=self.lastat)
                self.lastat = dt.now()
            else:
                now = dt.now()
                if now.day != self.lastat.day:
                    self.save(at=self.lastat)
                    logger.debug('just in today')

                record = Record(sentence=raw, at=now, passed=(now - self.lastat).total_seconds())
                self.buffer.append(record)
                if len(self.buffer) == self.full:
                    self.save(at=now)

                self.lastat = now

    # def run(self) -> None:
    #     while True:
    #         rows: List[Record] = self.qp.get()
    #         now = dt.now()
    #         name = self.nameformat % (now.year, now.month, now.day)
    #         file = self.path / name  # pathlib
    #         exists = file.exists()
    #         with self.locker:  # 念の為
    #             with closing(sqlite3.connect(str(file))) as db:
    #                 cursor = db.cursor()
    #                 if exists is False:
    #                     self.create(cursor=cursor)
    #                 for ooo in rows:
    #                     query = 'insert into sentence(at,ds,nmea) values(?,?,?)'
    #                     cursor.execute(query, [ooo.at.strftime(self.dateformat), ooo.passed, ooo.sentence])
    #                 logger.info('+++ %d records was saved to %s' % (len(rows), file))
    #                 cursor.close()
    #                 db.commit()  # never forget
