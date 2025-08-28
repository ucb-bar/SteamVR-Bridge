import ctypes.wintypes

import xr


class WindowsPerformanceCounter:
    """
    Performance counter used to get accurate system time on Windows platform.
    """
    def __init__(self, instance: xr.Instance):
        self.instance = instance
        self.pc_time = ctypes.wintypes.LARGE_INTEGER()
        self.kernel32 = ctypes.WinDLL("kernel32")
        self.pxr_convert_win32_performance_counter_to_time_khr = ctypes.cast(
            xr.get_instance_proc_addr(
                instance=self.instance,
                name="xrConvertWin32PerformanceCounterToTimeKHR",
            ),
            xr.PFN_xrConvertWin32PerformanceCounterToTimeKHR,
        )

    def time_from_perf_counter(self, performance_counter: ctypes.wintypes.LARGE_INTEGER) -> xr.Time:
        xr_time = xr.Time()
        result = self.pxr_convert_win32_performance_counter_to_time_khr(
            self.instance,
            ctypes.pointer(performance_counter),
            ctypes.byref(xr_time),
        )
        result = xr.check_result(result)
        if result.is_exception():
            raise result
        return xr_time

    def get(self):
        self.kernel32.QueryPerformanceCounter(ctypes.byref(self.pc_time))
        return self.time_from_perf_counter(self.instance, self.pc_time)
