from logging import Logger
from typing import Optional

from src.core.terminal_window_manager_v4.core.constants import (
    MAIN_WINDOW_HEIGHT,
    MAIN_WINDOW_WIDTH,
    MAX_WINDOWS_PER_COLUMN,
)
from src.core.terminal_window_manager_v4.twm_v4 import SecondaryWindow, WinType


class WindowPropertiesCalculator:
    def __init__(self, logger: Logger) -> None:
        self.logger = logger

    def calculate_main_window_properties(
        self, window_type: WinType, slot: Optional[int] = None
    ) -> tuple[int, int, int, int]:
        if slot is not None and window_type in (WinType.ACCEPTED, WinType.DENIED):
            width = MAIN_WINDOW_WIDTH
            height = MAIN_WINDOW_HEIGHT

            if window_type == WinType.ACCEPTED:
                x_pos = -width * (1 + slot // MAX_WINDOWS_PER_COLUMN)
            elif window_type == WinType.DENIED:
                x_pos = -1920 + width * (slot // MAX_WINDOWS_PER_COLUMN)

            y_pos = height * (slot % MAX_WINDOWS_PER_COLUMN)

        elif window_type is WinType.SERVER:
            width = 700
            height = 400
            x_pos = -1920
            y_pos = 640

        self.logger.info(
            f"Calculated properties for {window_type.name} window at slot {slot}: "
            f"({width}, {height}, {x_pos}, {y_pos})."
        )

        return width, height, x_pos, y_pos

    def calculate_secondary_window_properties(
        self, slot: int, secondary_windows: list[SecondaryWindow]
    ) -> list[tuple[int, int, int, int]]:
        properties = []
        x_pos_offset = MAIN_WINDOW_WIDTH
        y_pos_offset = 0

        for window in secondary_windows:
            width = window.width
            height = window.height

            if x_pos_offset - width < 0:
                x_pos_offset = MAIN_WINDOW_WIDTH
                y_pos_offset += height

            x_pos = (
                x_pos_offset
                - width
                - MAIN_WINDOW_WIDTH * (1 + slot // MAX_WINDOWS_PER_COLUMN)
            )
            y_pos = y_pos_offset + (
                MAIN_WINDOW_HEIGHT * (slot % MAX_WINDOWS_PER_COLUMN)
            )

            props = (width, height, x_pos, y_pos)
            properties.append(props)

            x_pos_offset -= width

        self.logger.info(
            f"Secondary properties for {[window.name for window in secondary_windows]} "
            f"calculated are {properties}"
        )

        return properties
