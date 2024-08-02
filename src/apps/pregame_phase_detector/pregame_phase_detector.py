import asyncio
import time
from typing import Optional

import cv2 as cv
import mss
import numpy as np
from skimage.metrics import structural_similarity as ssim
from websockets import WebSocketClientProtocol

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
from src.connection import websocket
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


async def capture_window(area: dict[str, int]):
    with mss.mss() as sct:
        img = sct.grab(area)
    return np.array(img)


async def compare_images(
    image_a: cv.typing.MatLike, image_b: cv.typing.MatLike
) -> float:
    return ssim(image_a, image_b)


async def capture_and_process_image(
    alias: str, capture_area: dict, template: cv.typing.MatLike
) -> float:
    frame = await capture_window(capture_area)
    gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

    match_value = await compare_images(gray_frame, template)

    window_name = next(
        (window.name for window in SECONDARY_WINDOWS if alias in window.name), None
    )

    if window_name:
        cv.imshow(window_name, gray_frame)

    if cv.waitKey(1) == ord("q"):
        return 0.0

    return match_value


async def detect_hero_pick():
    return await capture_and_process_image(
        "hero_pick_scanner", HERO_PICK_AREA, HERO_PICK_TEMPLATE
    )


async def detect_starting_buy():
    return await capture_and_process_image(
        "starting_buy_scanner", STARTING_BUY_AREA, STARTING_BUY_TEMPLATE
    )


async def detect_dota_tab_out():
    return await capture_and_process_image(
        "dota_tab_scanner", DOTA_TAB_AREA, DOTA_TAB_TEMPLATE
    )


async def detect_desktop_tab_out():
    return await capture_and_process_image(
        "desktop_tab_scanner", DESKTOP_TAB_AREA, DESKTOP_TAB_TEMPLATE
    )


async def detect_settings_screen():
    return await capture_and_process_image(
        "settings_scanner", SETTINGS_AREA, SETTINGS_TEMPLATE
    )


async def detect_in_game():
    return await capture_and_process_image(
        "in_game_scanner", IN_GAME_AREA, IN_GAME_TEMPLATE
    )


async def scan_screen_for_matches() -> dict[str, float]:
    (
        hero_pick_result,
        starting_buy_result,
        dota_tab_out_result,
        desktop_tab_out_result,
        settings_screen_result,
        in_game_result,
    ) = await asyncio.gather(
        detect_hero_pick(),
        detect_starting_buy(),
        detect_dota_tab_out(),
        detect_desktop_tab_out(),
        detect_settings_screen(),
        detect_in_game(),
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


async def set_state_finding_game() -> tuple[Tabbed, PickPhase]:
    game_phase = PickPhase()
    tabbed = Tabbed()
    game_phase.finding_game = True  # initial game phase
    print("\n\n\n\n\n\n\nWaiting to find a game...")  # a few newlines to
    # make some space for reading outputs in cli below the secondary windows.
    return tabbed, game_phase


async def set_state_game_found(
    tabbed: Tabbed, game_phase: PickPhase, ws: Optional[WebSocketClientProtocol]
) -> tuple[Tabbed, PickPhase]:
    tabbed.in_game = True
    game_phase.hero_pick = True
    print("\nFound a game !")
    if ws:
        await websocket.send_json_requests(ws, SCENE_CHANGE_IN_GAME, logger)
    return tabbed, game_phase


async def set_state_hero_pick(
    tabbed: Tabbed, game_phase: PickPhase, ws: Optional[WebSocketClientProtocol]
) -> tuple[Tabbed, PickPhase]:
    tabbed.in_game = True
    game_phase.hero_pick = True
    print("\nBack to hero select !")
    if ws:
        await websocket.send_json_requests(ws, SCENE_CHANGE_DSLR_MOVE_HERO_PICK, logger)
    return tabbed, game_phase


async def set_state_starting_buy(
    tabbed: Tabbed, game_phase: PickPhase, ws: Optional[WebSocketClientProtocol]
) -> tuple[Tabbed, PickPhase]:
    tabbed.in_game = True
    game_phase.starting_buy = True
    print("\nStarting buy !")
    if ws:
        await websocket.send_json_requests(ws, DSLR_MOVE_STARTING_BUY, logger)
    return tabbed, game_phase


async def set_state_vs_screen(
    tabbed: Tabbed, game_phase: PickPhase, ws: Optional[WebSocketClientProtocol]
) -> tuple[Tabbed, PickPhase]:
    tabbed.in_game = True
    game_phase.versus_screen = True
    if ws:
        await websocket.send_json_requests(ws, DSLR_HIDE_VS_SCREEN, logger)
    print("\nWe are in vs screen !")
    return tabbed, game_phase


async def set_state_in_game(
    tabbed: Tabbed, game_phase: PickPhase, ws: Optional[WebSocketClientProtocol]
) -> tuple[Tabbed, PickPhase]:
    tabbed.in_game = True
    game_phase.in_game = True
    if ws:
        await websocket.send_json_requests(ws, SCENE_CHANGE_IN_GAME, logger)
    print("\nWe are in now game !")
    return tabbed, game_phase


async def set_state_dota_menu(
    tabbed: Tabbed, game_phase: PickPhase, ws: Optional[WebSocketClientProtocol]
) -> tuple[Tabbed, PickPhase]:
    tabbed.to_dota_menu = True
    game_phase.unknown = True
    if ws:
        await websocket.send_json_requests(ws, DSLR_HIDE_VS_SCREEN, logger)
    print("\nWe are in Dota Menus !")
    return tabbed, game_phase


async def set_state_desktop(
    tabbed: Tabbed, game_phase: PickPhase
) -> tuple[Tabbed, PickPhase]:
    tabbed.to_desktop = True
    game_phase.unknown = True
    print("\nWe are on desktop !")
    return tabbed, game_phase


async def set_state_settings_screen(
    tabbed: Tabbed, game_phase: PickPhase, ws: Optional[WebSocketClientProtocol]
) -> tuple[Tabbed, PickPhase]:
    tabbed.to_settings_screen = True
    game_phase.unknown = True
    if ws:
        await websocket.send_json_requests(
            ws,
            "src/apps/pregame_phase_detector/ws_requests/dslr_hide_vs_screen.json",
            logger,
        )
    print("\nWe are in settings !")
    return tabbed, game_phase


async def confirm_transition_to_vs_screen(
    tabbed: Tabbed,
    game_phase: PickPhase,
    target_value: float,
    ws: Optional[WebSocketClientProtocol],
) -> tuple[Tabbed, PickPhase]:
    """Nothing matches: we might be in vs screen. Make sure nothing keeps
    matching for a while before asserting this, because we might just
    otherwise be in some transitional state: for example, in dota tab-out;
    nothing will match when opening the settings screen, until its opening
    animation has fully played out, then, the settings screen template will
    match."""
    start_time = time.time()
    duration = 0.5
    target = target_value
    print("\nNo matches detected !")
    mute_ssim_prints.set()

    while time.time() - start_time < duration:
        print(
            f"Checking for vs screen... ({time.time() - start_time:.4f}s elapsed.)",
            end="\r",
        )
        ssim_matches = await scan_screen_for_matches()

        if max(ssim_matches.values()) >= target:
            print("\nNot in vs screen !")
            break
        elif time.time() - start_time >= duration:
            # The condition was true for the entire 0.5 seconds
            tabbed, game_phase = await set_state_vs_screen(tabbed, game_phase, ws)
            break
    mute_ssim_prints.clear()
    return tabbed, game_phase


async def wait_for_settings_screen_fade_out(tabbed: Tabbed) -> Tabbed:
    """Delay to allow time for the settings screen closing animation. Does
    not trigger when tabbing out to Desktop since in this case the settings
    closing animation does not play."""
    tabbed.to_settings_screen = False
    await asyncio.sleep(0.25)
    return tabbed


async def wait_for_starting_buy_screen_fade_out(
    game_phase: PickPhase,
) -> PickPhase:
    """Delay to allow time for the starting buy screen fade out when
    transitioning to the hero select or settings screen. Does not trigger
    if tabbing out to Dota or Desktop since in those cases the progressive fade from
    starting buy screen does not occur."""
    game_phase.starting_buy = False
    await asyncio.sleep(0.25)
    return game_phase


async def detect_pregame_phase(
    ws: Optional[WebSocketClientProtocol], socket_handler: PreGamePhaseHandler
):
    #  ----------- The code below is not part of the main logic ------------
    new_capture = False  # Set manually to capture new screen area
    while new_capture:
        await capture_new_area(
            NEW_CAPTURE_AREA, "src/apps/pregame_phase_detector/opencv/XXX.jpg"
        )
    #  ----------- The code above is not part of the main logic ------------

    tabbed, game_phase = await set_state_finding_game()
    target = 0.7  # target value for ssim
    while not socket_handler.stop_event.is_set():

        ssim_match = await scan_screen_for_matches()

        if (
            tabbed.to_settings_screen
            and ssim_match["settings"] < target
            and ssim_match["desktop_tab"] < target
        ):
            tabbed = await wait_for_settings_screen_fade_out(tabbed)
            continue

        if (
            game_phase.starting_buy
            and ssim_match["starting_buy"] < target
            and ssim_match["dota_tab"] < target
            and ssim_match["desktop_tab"] < target
        ):
            game_phase = await wait_for_starting_buy_screen_fade_out(game_phase)
            continue

        if ssim_match["hero_pick"] >= target and game_phase.finding_game:
            tabbed, game_phase = await set_state_game_found(tabbed, game_phase, ws)
            continue

        if not game_phase.finding_game:

            if ssim_match["starting_buy"] >= target and not game_phase.starting_buy:
                tabbed, game_phase = await set_state_starting_buy(
                    tabbed, game_phase, ws
                )
                continue

            if (
                ssim_match["hero_pick"] >= target > ssim_match["starting_buy"]
                and ssim_match["settings"] < target
                and ssim_match["desktop_tab"] < target
                and not game_phase.hero_pick
            ):
                tabbed, game_phase = await set_state_hero_pick(tabbed, game_phase, ws)
                continue

            if ssim_match["dota_tab"] >= target and not tabbed.to_dota_menu:
                tabbed, game_phase = await set_state_dota_menu(tabbed, game_phase, ws)
                continue

            if ssim_match["desktop_tab"] >= target and not tabbed.to_desktop:
                tabbed, game_phase = await set_state_desktop(tabbed, game_phase)
                continue

            if ssim_match["settings"] >= target and not tabbed.to_settings_screen:
                tabbed, game_phase = await set_state_settings_screen(
                    tabbed, game_phase, ws
                )
                continue

            if ssim_match["in_game"] >= target and not game_phase.in_game:
                tabbed, game_phase = await set_state_in_game(tabbed, game_phase, ws)
                continue

            if max(ssim_match.values()) < target and not game_phase.versus_screen:
                tabbed, game_phase = await confirm_transition_to_vs_screen(
                    tabbed, game_phase, target, ws
                )
                continue

        await asyncio.sleep(0.01)


async def capture_new_area(capture_area: dict[str, int], filename: str):
    frame = await capture_window(capture_area)
    gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    cv.imshow("new_area_capture", gray_frame)
    secondary_windows_spawned.set()
    cv.imwrite(filename, gray_frame)


async def run_main_task(
    slot: int,
    socket_handler: PreGamePhaseHandler,
    ws: Optional[WebSocketClientProtocol],
):
    mute_ssim_prints.set()
    main_task = asyncio.create_task(detect_pregame_phase(ws, socket_handler))

    await secondary_windows_spawned.wait()
    await twm.manage_secondary_windows(slot, SECONDARY_WINDOWS)
    mute_ssim_prints.clear()
    await main_task
    return None


async def main():
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

        ws = await websocket.establish_ws_connection(STREAMERBOT_WS_URL, logger)
        await run_main_task(slot, socket_server_handler, ws)

    except Exception as e:
        print(f"Unexpected error of type: {type(e).__name__}: {e}")
        logger.exception(f"Unexpected error: {e}")
        raise

    finally:
        if socket_server_task:
            socket_server_task.cancel()
            await socket_server_task
        if ws:
            await ws.close()
        if slots_db_conn:
            await slots_db_conn.close()
        cv.destroyAllWindows()


if __name__ == "__main__":
    asyncio.run(main())
    print_countdown()
