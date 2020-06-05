import time
import os
import sqlite3
from contextlib import closing
from threading import Thread
from datetime import datetime as dt
import queue
from loguru import logger


class DBSession(Thread):

    def __init__(self, *, ymd: str, interval: int):

        super().__init__()
        self.daemon = True
        self.name = 'DBSession'

        self.ymd = ymd

        self.many = Common.SQlite3.many * interval
        self.holdsecs = Common.SQlite3.holdsecs * interval
        self.lastcommit = dt.utcnow()
        # self.buffer = []

        self.q = queue.Queue(maxsize=Common.SQlite3.many * interval)

        self.silence = Common.SQlite3.limitsecs
        self.logger = logging.getLogger('AISLogger')

    def currentRows(self, *, ymd: str) -> int:

        counter = 0

        # file = os.path.join(*[Common.dbPath, ymd + '.db'])
        file = Common.dbname(ymd=ymd)
        if os.path.exists(file):
            with closing(sqlite3.connect(file)) as db:
                db.row_factory = sqlite3.Row
                cursor = db.cursor()
                query = 'select max(id) as max from sentence'
                with Common.SQlite3.lock:
                    cursor.execute(query)
                    row = cursor.fetchone()
                counter = row['max']
        else:
            pass

        return counter

    def run(self):

        self.logger.debug('Start')

        def save(*, force: bool = True):

            size = self.q.qsize()
            if size:
                doit = False
                now = dt.utcnow()
                secs = (now - self.lastcommit).total_seconds()
                if force is False:
                    if size == self.many or secs > self.holdsecs:
                        doit = True
                else:
                    doit = True
                if doit:
                    self.lastcommit = now

                    # file = os.path.join(*[Common.dbPath, self.ymd + '.db'])
                    file = Common.dbname(ymd=self.ymd)
                    exists = os.path.exists(file)
                    with Common.SQlite3.lock:  # 念の為
                        with closing(sqlite3.connect(file)) as db:
                            cursor = db.cursor()

                            if exists is False:
                                query = "CREATE TABLE 'sentence' ( `id` INTEGER NOT NULL DEFAULT 0 PRIMARY KEY, `hms` TEXT NOT NULL DEFAULT '',`header` TEXT NOT NULL DEFAULT '' ,`nmea` TEXT NOT NULL DEFAULT '', `ctag` TEXT NOT NULL DEFAULT '' )"
                                cursor.execute(query)

                                query = 'create index idindex on sentence(id)'
                                cursor.execute(query)

                                msg = 'created %s' % (file,)
                                self.logger.debug(msg=msg)

                            column = [tuple()] * size
                            for index in range(size):
                                column[index] = self.q.get()
                            query = 'insert into sentence(id,hms,header,nmea,ctag) values(?,?,?,?,?)'
                            ss = time.time()
                            cursor.executemany(query, column)
                            db.commit()
                            es = time.time()

                    msg = '%d records are saved after %d secs (%d)' % (size, secs, es-ss)
                    self.logger.debug(msg=msg)

        while True:

            if Common.Retrieve.start:
                Common.Retrieve.start = False  # notice!
                save()
                Common.Retrieve.ready.set()  # notice!
                pass
            else:
                try:
                    src = Common.SQlite3.quePoint.get(timeout=self.silence)
                except queue.Empty as e:
                    save()
                    pass
                else:

                    id = src['id']
                    header = src['header']
                    nmea = src['nmea']
                    ymd = src['ymd']
                    hms = src['hms']
                    ctag = src['ctag']

                    if ymd != self.ymd:
                        save()
                        Common.Daily.ymd.put(self.ymd)
                        self.ymd = ymd

                    self.q.put((id, hms, header, nmea, ctag))
                    save(force=False)