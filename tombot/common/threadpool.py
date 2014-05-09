from Queue import Queue
from threading import Thread


class Worker(Thread):
    def __init__(self, tasks):
        super(Worker, self).__init__()
        self.daemon = False
        self.tasks = tasks
        self.start()

    def run(self):
        while True:
            task, args, kwargs = self.tasks.get()
            task(*args, **kwargs)
            self.tasks.task_done()


class ThreadPool(object):
    def __init__(self, num_threads):
        self.tasks = Queue(num_threads)
        for _ in range(num_threads):
            Worker(self.tasks)

    def add_task(self, func, *args, **kwargs):
        self.tasks.put((func, args, kwargs))

    def wait_completion(self):
        self.task.join()
