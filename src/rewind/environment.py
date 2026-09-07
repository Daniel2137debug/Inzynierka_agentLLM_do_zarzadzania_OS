


import pathlib  
import os
import ctypes
import winreg
import platform

def get_desktop_path() -> str:
    #I didnt use home due to OneDrive what could replace path to desktop
    open_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
    desktop_path, _ = winreg.QueryValueEx(open_key, "Desktop")
    winreg.CloseKey(open_key)
    return desktop_path
    


def get_env_data()-> dict[str,str]:
    """give you a data about the environment, like current working directory, home directory, desktop path, os name and version, and if the user is admin or not"""
    return {
        "home_dir": str(pathlib.Path.home()),
        "current_dir": os.getcwd(),
        "os_name": platform.system(),
        "os_version": platform.release(),
        "is_admin": str(bool(ctypes.windll.shell32.IsUserAnAdmin())),
        "desktop_dir": get_desktop_path()
    }
