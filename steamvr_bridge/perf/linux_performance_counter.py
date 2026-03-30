import ctypes
import time

import xr


class LinuxPerformanceCounter:
    """
    Performance counter used to get accurate system time on UNIX platform.
    """
    def __init__(self, instance: xr.Instance):
        self.instance = instance
        self.timespec_time = xr.timespec()
        self.pxrConvertTimespecTimeToTimeKHR = ctypes.cast(
            xr.get_instance_proc_addr(
                instance=self.instance,
                name="xrConvertTimespecTimeToTimeKHR",
            ),
            xr.PFN_xrConvertTimespecTimeToTimeKHR,
        )

    def time_from_timespec(self, timespec_time: xr.timespec) -> xr.Time:
        xr_time = xr.Time()
        result = self.pxrConvertTimespecTimeToTimeKHR(
            self.instance,
            ctypes.pointer(timespec_time),
            ctypes.byref(xr_time),
        )
        result = xr.check_result(result)
        if result.is_exception():
            raise result
        return xr_time

    def get(self):
        time_float = time.clock_gettime(time.CLOCK_MONOTONIC)
        self.timespec_time.tv_sec = int(time_float)
        self.timespec_time.tv_nsec = int((time_float % 1) * 1e9)
        return self.time_from_timespec(self.timespec_time)

