from functools import partial


class Executor:
    def __init__(self, loop=None, executor=None, logger=None):
        self.EXECUTOR = executor
        self.configure_executor()
        self.loop = loop

    def configure_executor(self, max_workers: int = 10):
        if not self.EXECUTOR:
            from concurrent.futures import ThreadPoolExecutor
            self.EXECUTOR = ThreadPoolExecutor(max_workers=max_workers)

    def set_executor(self, executor):
        self.EXECUTOR = executor

    def get_executor(self):
        return self.EXECUTOR

    async def run(self, func, *args, **kwargs):
        return await self.loop.run_in_executor(self.EXECUTOR, partial(func, *args, **kwargs))

    def close(self):
        self.EXECUTOR.shutdown()
