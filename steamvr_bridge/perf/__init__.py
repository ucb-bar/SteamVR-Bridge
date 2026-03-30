import platform


if platform.system() == "Windows":
    import ctypes.wintypes  # noqa: F401
    from .windows_performance_counter import WindowsPerformanceCounter as PerformanceCounter  # noqa: F401
else:
    import ctypes  # noqa: F401
    from .linux_performance_counter import LinuxPerformanceCounter as PerformanceCounter  # noqa: F401

__all__ = ["PerformanceCounter"]
