import time



class WindowsPerformanceCounter:
    """
    Simple high-resolution clock wrapper for Windows.
    """

    def __init__(self, instance: object | None = None):
        self.instance = instance

    def get(self):
        return time.perf_counter_ns()
