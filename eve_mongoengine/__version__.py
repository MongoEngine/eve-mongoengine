# Project Version

# This file must remain compatible with
# both Python >= 2.6 and Python 3.3+

VERSION = (0, 1, 0)     # 0.1.0

def get_version():
    if isinstance(VERSION[-1], int):
        return '.'.join(map(str, VERSION))
    return '.'.join(map(str, VERSION[:-1])) + VERSION[-1]

