import sys

if sys.platform.startswith("win"):
    from .windows_list_win32 import WindowsList
elif sys.platform.startswith("darwin"):
    from .windows_list_osx import WindowsList
else:
    from .windows_list_x11 import WindowsList
