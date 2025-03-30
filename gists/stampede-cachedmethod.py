# https://github.com/tkem/cachetools/issues/294
import threading
from time import sleep

import cachetools

NUM_THREADS = 1000
CACHE_TTL_SECONDS = 3600  # one hour
# INFO = True


class Cached:

    def __init__(self):
        self.cache = cachetools.TTLCache(maxsize=1, ttl=CACHE_TTL_SECONDS)
        self.lock = threading.Lock()

    @cachetools.cachedmethod(lambda self: self.cache, lock=lambda self: self.lock)
    def get_value(self):
        print("get_value")
        sleep(1)
        return 42


class MyThread(threading.Thread):
    def __init__(self, id, cached):
        threading.Thread.__init__(self)
        self.thread_name = str(id)
        self.thread_ID = id
        self.cached = cached

    def run(self):
        self.cached.get_value()


cached = Cached()
threads = []
for i in range(0, NUM_THREADS):
    t = MyThread(i, cached)
    threads.append(t)
    t.start()
for t in threads:
    t.join()
