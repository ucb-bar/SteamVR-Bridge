import time


class LinuxPerformanceCounter:
    """
    Simple monotonic clock wrapper for UNIX-like platforms.
    """

    def __init__(self, instance: object | None = None):
        self.instance = instance

    def get(self):
        return time.monotonic_ns()
