import xr


def check_raw_result(result, message: str | None = None):
    """
    Normalize ctypes/OpenXR function-pointer return values before delegating to pyopenxr.

    Some extension entry points return a plain ``int`` instead of ``xr.Result`` when invoked
    through a PFN function pointer. ``xr.check_result()`` expects the enum-like wrapper.
    """
    if not isinstance(result, xr.Result):
        result = xr.Result(result)
    return xr.check_result(result, message)
