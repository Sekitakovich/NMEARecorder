import psutil
from dataclasses import dataclass
from threading import Thread
import time


@dataclass()
class Stats(object):
    # status: str = ''
    # threads: int = 0
    cpuPercent: float = 0.0
    memPercent: float = 0.0
    core: int = 0


class Patrol(Thread):
    def __init__(self, *, pid: int, interval: float = 3):
        super().__init__()
        self.daemon = True
        self.p = psutil.Process(pid=pid)
        self.interval = interval

        self.stats = Stats()
        self.cpu = Thread(target=self.cpuChecker, name='CPU', daemon=True)

    def cpuChecker(self):
        interval: int = 1
        while True:
            self.stats.cpuPercent = round(self.p.cpu_percent(interval=5),2)
            time.sleep(interval)


    def run(self) -> None:
        self.cpu.start()
        while True:
            # self.stats.cpuPercent = round(self.p.cpu_percent(interval=self.interval - 1),2)
            self.stats.memPercent = round(self.p.memory_percent(), 2)
            # self.stats.status = self.p.status()
            self.stats.core = self.p.cpu_num()
            # self.stats.threads = self.p.num_threads()
            time.sleep(self.interval)
