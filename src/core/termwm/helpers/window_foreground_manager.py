from logging import Logger
from typing import Optional

import aiosqlite
import pygetwindow
import win32con
import win32gui

from src.core.termwm import slots_db_handler as sdh
from src.core.termwm.core.constants import SERVER_WINDOW_NAME
from src.core.termwm.helpers.window_adjuster import WindowAdjuster


class WindowForegroundManager:
    def __init__(self, adjuster: WindowAdjuster, logger: Logger) -> None:
        self.adjuster = adjuster
        self.logger = logger

    async def set_windows_to_topmost(
        self, conn: aiosqlite.Connection, server: Optional[bool] = False
    ) -> None:
        windows_names = (
            await sdh.get_all_names(conn) if not server else [SERVER_WINDOW_NAME]
        )
        windows_names.reverse()
        for name in windows_names:
            window = win32gui.FindWindow(None, name)
            if window:
                win32gui.SetWindowPos(
                    window,
                    win32con.HWND_TOPMOST,
                    0,
                    0,
                    0,
                    0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
                )
        self.logger.info("Windows set to topmost.")

    async def unset_windows_to_topmost(
        self, conn: aiosqlite.Connection, server: Optional[bool] = False
    ) -> None:
        windows_names = (
            await sdh.get_all_names(conn) if not server else [SERVER_WINDOW_NAME]
        )
        for name in windows_names:
            window = win32gui.FindWindow(None, name)
            if window:
                win32gui.SetWindowPos(
                    window,
                    win32con.HWND_NOTOPMOST,
                    0,
                    0,
                    0,
                    0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
                )
        self.logger.info("Windows unset from topmost.")

    async def restore_all_windows(
        self, conn: aiosqlite.Connection, server: Optional[bool] = False
    ) -> None:
        windows_names = (
            await sdh.get_all_names(conn) if not server else [SERVER_WINDOW_NAME]
        )
        for name in windows_names:
            window = pygetwindow.getWindowsWithTitle(name)
            if window:
                window = window[0]
                window.restore()
        self.logger.info("All windows restored.")

    async def bring_windows_to_foreground(
        self, conn: aiosqlite.Connection, server: Optional[bool] = False
    ) -> None:
        await self.restore_all_windows(conn, server)
        await self.set_windows_to_topmost(conn, server)
        await self.unset_windows_to_topmost(conn, server)
        self.logger.info("Windows brought to foreground.")
