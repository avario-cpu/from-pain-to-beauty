import asyncio
from typing import Dict

import cv2 as cv
import mss
import numpy as np
from skimage.metrics import structural_similarity as ssim  # pylint: disable=E0611

from src.apps.pregame_phase_detector.core.constants import (
    DESKTOP_TAB_AREA,
    DESKTOP_TAB_TEMPLATE,
    DOTA_TAB_AREA,
    DOTA_TAB_TEMPLATE,
    HERO_PICK_AREA,
    HERO_PICK_TEMPLATE,
    IN_GAME_AREA,
    IN_GAME_TEMPLATE,
    SECONDARY_WINDOWS,
    SETTINGS_AREA,
    SETTINGS_TEMPLATE,
    STARTING_BUY_AREA,
    STARTING_BUY_TEMPLATE,
)
from src.apps.pregame_phase_detector.core.shared_events import (
    mute_ssim_prints,
    secondary_windows_spawned,
)


class ImageProcessor:
    async def capture_new_area(self, capture_area: dict[str, int], filename: str):
        while True:
            frame = await self.capture_window(capture_area)
            gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            cv.imshow("new_area_capture", gray_frame)
            secondary_windows_spawned.set()
            cv.imwrite(filename, gray_frame)
            if cv.waitKey(1) == ord("q"):
                break
            await asyncio.sleep(0.1)

    async def capture_window(self, area: dict[str, int]):
        with mss.mss() as sct:
            img = sct.grab(area)
        return np.array(img)

    def compare_images(
        self, image_a: cv.typing.MatLike, image_b: cv.typing.MatLike
    ) -> float:
        return ssim(image_a, image_b)

    async def capture_and_process_image(
        self, alias: str, capture_area: dict, template: cv.typing.MatLike
    ) -> float:
        frame = await self.capture_window(capture_area)
        gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        match_value = self.compare_images(gray_frame, template)

        window_name = next(
            (window.name for window in SECONDARY_WINDOWS if alias in window.name), None
        )

        if window_name:
            cv.imshow(window_name, gray_frame)

        if cv.waitKey(1) == ord("q"):
            return 0.0

        return match_value

    async def detect_hero_pick(self):
        return await self.capture_and_process_image(
            "hero_pick_scanner", HERO_PICK_AREA, HERO_PICK_TEMPLATE
        )

    async def detect_starting_buy(self):
        return await self.capture_and_process_image(
            "starting_buy_scanner", STARTING_BUY_AREA, STARTING_BUY_TEMPLATE
        )

    async def detect_dota_tab_out(self):
        return await self.capture_and_process_image(
            "dota_tab_scanner", DOTA_TAB_AREA, DOTA_TAB_TEMPLATE
        )

    async def detect_desktop_tab_out(self):
        return await self.capture_and_process_image(
            "desktop_tab_scanner", DESKTOP_TAB_AREA, DESKTOP_TAB_TEMPLATE
        )

    async def detect_settings_screen(self):
        return await self.capture_and_process_image(
            "settings_scanner", SETTINGS_AREA, SETTINGS_TEMPLATE
        )

    async def detect_in_game(self):
        return await self.capture_and_process_image(
            "in_game_scanner", IN_GAME_AREA, IN_GAME_TEMPLATE
        )

    async def scan_screen_for_matches(self) -> Dict[str, float]:
        (
            hero_pick_result,
            starting_buy_result,
            dota_tab_out_result,
            desktop_tab_out_result,
            settings_screen_result,
            in_game_result,
        ) = await asyncio.gather(
            self.detect_hero_pick(),
            self.detect_starting_buy(),
            self.detect_dota_tab_out(),
            self.detect_desktop_tab_out(),
            self.detect_settings_screen(),
            self.detect_in_game(),
        )

        secondary_windows_spawned.set()

        combined_results = {
            "hero_pick": hero_pick_result,
            "starting_buy": starting_buy_result,
            "dota_tab": dota_tab_out_result,
            "desktop_tab": desktop_tab_out_result,
            "settings": settings_screen_result,
            "in_game": in_game_result,
        }

        key_aliases = {
            "hero_pick": "HP",
            "starting_buy": "SB",
            "dota_tab": "DT",
            "desktop_tab": "DKT",
            "settings": "SET",
            "in_game": "IG",
        }

        formatted_combined_results = ", ".join(
            [
                f"{key_aliases[key]}:{value:.2f}"
                for key, value in combined_results.items()
            ]
        )

        if not mute_ssim_prints.is_set():
            print(f"SSMIs: {formatted_combined_results}", end="\r")

        return combined_results
