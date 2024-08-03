import asyncio
import time

import cv2 as cv
import mss
import numpy as np
from skimage.metrics import structural_similarity as ssim

from src.apps.pregame_phase_detector.core.constants import (
    DESKTOP_TAB_AREA,
    DESKTOP_TAB_TEMPLATE,
    DOTA_TAB_AREA,
    DOTA_TAB_TEMPLATE,
    DSLR_HIDE_VS_SCREEN,
    DSLR_MOVE_STARTING_BUY,
    HERO_PICK_AREA,
    HERO_PICK_TEMPLATE,
    IN_GAME_AREA,
    IN_GAME_TEMPLATE,
    NEW_CAPTURE_AREA,
    SCENE_CHANGE_DSLR_MOVE_HERO_PICK,
    SCENE_CHANGE_IN_GAME,
    SECONDARY_WINDOWS,
    SETTINGS_AREA,
    SETTINGS_TEMPLATE,
    STARTING_BUY_AREA,
    STARTING_BUY_TEMPLATE,
)
from src.apps.pregame_phase_detector.core.pick_phase import PickPhase
from src.apps.pregame_phase_detector.core.socket_handler import PreGamePhaseHandler
from src.apps.pregame_phase_detector.core.tabbed import Tabbed
from src.connection.websocket_client import WebSocketClient
from src.core import terminal_window_manager_v4 as twm
from src.core.constants import STREAMERBOT_WS_URL, SUBPROCESSES_PORTS
from src.core.constants import TERMINAL_WINDOW_SLOTS_DB_FILE_PATH as SLOTS_DB
from src.utils.helpers import construct_script_name, print_countdown
from src.utils.logging_utils import setup_logger
from src.utils.script_initializer import setup_script

SCRIPT_NAME = construct_script_name(__file__)
logger = setup_logger(SCRIPT_NAME, "DEBUG")

PORT = SUBPROCESSES_PORTS["pregame_phase_detector"]

secondary_windows_spawned = asyncio.Event()
mute_ssim_prints = asyncio.Event()


class ImageProcessor:
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

    async def scan_screen_for_matches(self) -> dict[str, float]:
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

        formatted_combined_results = ", ".join(
            [f"{alias[:2]}:{value:.2f}" for alias, value in combined_results.items()]
        )

        if not mute_ssim_prints.is_set():
            print(f"SSMIs: {formatted_combined_results}", end="\r")

        return combined_results


class GameStateManager:
    def __init__(self, image_processor: ImageProcessor, ws: WebSocketClient):
        self.image_processor = image_processor
        self.ws = ws
        self.tabbed = Tabbed()
        self.game_phase = PickPhase()

    async def set_state_finding_game(self):
        self.game_phase.finding_game = True  # initial game phase
        print(
            "\n\n\n\n\n\n\nWaiting to find a game..."
        )  # to avoid forefront blocking secondary windows

    async def set_state_game_found(self):
        self.tabbed.in_game = True
        self.game_phase.hero_pick = True
        print("\nFound a game !")
        if self.ws:
            await self.ws.send_json_requests(SCENE_CHANGE_IN_GAME)

    async def set_state_hero_pick(self):
        self.tabbed.in_game = True
        self.game_phase.hero_pick = True
        print("\nBack to hero select !")
        if self.ws:
            await self.ws.send_json_requests(SCENE_CHANGE_DSLR_MOVE_HERO_PICK)

    async def set_state_starting_buy(self):
        self.tabbed.in_game = True
        self.game_phase.starting_buy = True
        print("\nStarting buy !")
        if self.ws:
            await self.ws.send_json_requests(DSLR_MOVE_STARTING_BUY)

    async def set_state_vs_screen(self):
        self.tabbed.in_game = True
        self.game_phase.versus_screen = True
        if self.ws:
            await self.ws.send_json_requests(DSLR_HIDE_VS_SCREEN)
        print("\nWe are in vs screen !")

    async def set_state_in_game(self):
        self.tabbed.in_game = True
        self.game_phase.in_game = True
        if self.ws:
            await self.ws.send_json_requests(SCENE_CHANGE_IN_GAME)
        print("\nWe are in now game !")

    async def set_state_dota_menu(self):
        self.tabbed.to_dota_menu = True
        self.game_phase.unknown = True
        if self.ws:
            await self.ws.send_json_requests(DSLR_HIDE_VS_SCREEN)
        print("\nWe are in Dota Menus !")

    async def set_state_desktop(self):
        self.tabbed.to_desktop = True
        self.game_phase.unknown = True
        print("\nWe are on desktop !")

    async def set_state_settings_screen(self):
        self.tabbed.to_settings_screen = True
        self.game_phase.unknown = True
        if self.ws:
            await self.ws.send_json_requests(DSLR_HIDE_VS_SCREEN)
        print("\nWe are in settings !")

    async def confirm_transition_to_vs_screen(self, target_value: float):
        start_time = time.time()
        duration = 0.5
        print("\nNo matches detected !")
        mute_ssim_prints.set()

        while time.time() - start_time < duration:
            print(
                f"Checking for vs screen... ({time.time() - start_time:.4f}s elapsed.)",
                end="\r",
            )
            ssim_matches = await self.image_processor.scan_screen_for_matches()

            if max(ssim_matches.values()) >= target_value:
                print("\nNot in vs screen !")
                break
            elif time.time() - start_time >= duration:
                # The condition was true for the entire 0.5 seconds
                await self.set_state_vs_screen()
                break
        mute_ssim_prints.clear()

    async def wait_for_settings_screen_fade_out(self):
        self.tabbed.to_settings_screen = False
        await asyncio.sleep(0.25)

    async def wait_for_starting_buy_screen_fade_out(self):
        self.game_phase.starting_buy = False
        await asyncio.sleep(0.25)


class PreGamePhaseDetector:
    def __init__(self, socket_handler: PreGamePhaseHandler, ws_client: WebSocketClient):
        self.image_processor = ImageProcessor()
        self.state_manager = GameStateManager(self.image_processor, ws_client)
        self.socket_handler = socket_handler

    async def detect_pregame_phase(self):
        #  ----------- The code below is not part of the main logic ------------
        new_capture = False  # Set manually to capture new screen area
        while new_capture:
            await self.capture_new_area(
                NEW_CAPTURE_AREA, "src/apps/pregame_phase_detector/opencv/XXX.jpg"
            )
        #  ----------- The code above is not part of the main logic ------------

        await self.state_manager.set_state_finding_game()
        target = 0.7  # target value for ssim
        while not self.socket_handler.stop_event.is_set():

            ssim_match = await self.image_processor.scan_screen_for_matches()

            if (
                self.state_manager.tabbed.to_settings_screen
                and ssim_match["settings"] < target
                and ssim_match["desktop_tab"] < target
            ):
                await self.state_manager.wait_for_settings_screen_fade_out()
                continue

            if (
                self.state_manager.game_phase.starting_buy
                and ssim_match["starting_buy"] < target
                and ssim_match["dota_tab"] < target
                and ssim_match["desktop_tab"] < target
            ):
                await self.state_manager.wait_for_starting_buy_screen_fade_out()
                continue

            if (
                ssim_match["hero_pick"] >= target
                and self.state_manager.game_phase.finding_game
            ):
                await self.state_manager.set_state_game_found()
                continue

            if not self.state_manager.game_phase.finding_game:

                if (
                    ssim_match["starting_buy"] >= target
                    and not self.state_manager.game_phase.starting_buy
                ):
                    await self.state_manager.set_state_starting_buy()
                    continue

                if (
                    ssim_match["hero_pick"] >= target > ssim_match["starting_buy"]
                    and ssim_match["settings"] < target
                    and ssim_match["desktop_tab"] < target
                    and not self.state_manager.game_phase.hero_pick
                ):
                    await self.state_manager.set_state_hero_pick()
                    continue

                if (
                    ssim_match["dota_tab"] >= target
                    and not self.state_manager.tabbed.to_dota_menu
                ):
                    await self.state_manager.set_state_dota_menu()
                    continue

                if (
                    ssim_match["desktop_tab"] >= target
                    and not self.state_manager.tabbed.to_desktop
                ):
                    await self.state_manager.set_state_desktop()
                    continue

                if (
                    ssim_match["settings"] >= target
                    and not self.state_manager.tabbed.to_settings_screen
                ):
                    await self.state_manager.set_state_settings_screen()
                    continue

                if (
                    ssim_match["in_game"] >= target
                    and not self.state_manager.game_phase.in_game
                ):
                    await self.state_manager.set_state_in_game()
                    continue

                if (
                    max(ssim_match.values()) < target
                    and not self.state_manager.game_phase.versus_screen
                ):
                    await self.state_manager.confirm_transition_to_vs_screen(target)
                    continue

            await asyncio.sleep(0.01)

    async def capture_new_area(self, capture_area: dict[str, int], filename: str):
        frame = await self.image_processor.capture_window(capture_area)
        gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        cv.imshow("new_area_capture", gray_frame)
        secondary_windows_spawned.set()
        cv.imwrite(filename, gray_frame)


async def run_main_task(
    slot: int,
    detector: PreGamePhaseDetector,
):
    mute_ssim_prints.set()
    main_task = asyncio.create_task(detector.detect_pregame_phase())

    await secondary_windows_spawned.wait()
    await twm.manage_secondary_windows(slot, SECONDARY_WINDOWS)
    mute_ssim_prints.clear()
    await main_task
    return None


async def main():
    ws_client = None
    socket_server_task = None
    slots_db_conn = None
    try:
        slots_db_conn, slot = await setup_script(
            SCRIPT_NAME, SLOTS_DB, SECONDARY_WINDOWS
        )
        if slot is None:
            logger.error("No terminal window slot available, exiting.")
            return

        socket_server_handler = PreGamePhaseHandler(PORT, logger)
        socket_server_task = asyncio.create_task(
            socket_server_handler.run_socket_server()
        )

        ws_client = WebSocketClient(STREAMERBOT_WS_URL, logger)
        await ws_client.establish_connection()

        detector = PreGamePhaseDetector(socket_server_handler, ws_client)
        await run_main_task(slot, detector)

    except Exception as e:
        print(f"Unexpected error of type: {type(e).__name__}: {e}")
        logger.exception(f"Unexpected error: {e}")
        raise

    finally:
        if socket_server_task:
            socket_server_task.cancel()
            await socket_server_task
        if ws_client:
            await ws_client.close()
        if slots_db_conn:
            await slots_db_conn.close()
        cv.destroyAllWindows()


if __name__ == "__main__":
    asyncio.run(main())
    print_countdown()
