import asyncio
import logging
import time

import cv2 as cv
import mss
import numpy as np
from skimage.metrics import structural_similarity as ssim
from websockets import WebSocketClientProtocol

from src.conn import socks, websocket
from src.core import constants as const
from src.core import slots_db_handler as sdh
from src.core import terminal_window_manager_v4 as twm
from src.core import utils
from src.core.setup import setup_script_basics
from src.core.terminal_window_manager_v4 import SecondaryWindow, WinType

SCRIPT_NAME = utils.construct_script_name(__file__)
PORT = const.SUBPROCESSES_PORTS[SCRIPT_NAME]
URL = const.STREAMERBOT_WS_URL
DB = const.SLOTS_DB_FILE_PATH
SECONDARY_WINDOWS = [
    SecondaryWindow("first_scanner", 150, 80),
    SecondaryWindow("second_scanner", 150, 80),
    SecondaryWindow("third_scanner", 150, 80),
    SecondaryWindow("fourth_scanner", 150, 80),
    SecondaryWindow("fifth_scanner", 150, 80),
    SecondaryWindow("sixth_scanner", 150, 100),
]

DOTA_TAB_AREA = {"left": 1860, "top": 10, "width": 60, "height": 40}
STARTING_BUY_AREA = {"left": 860, "top": 120, "width": 400, "height": 30}
IN_GAME_AREA = {"left": 1820, "top": 1020, "width": 80, "height": 60}
PLAY_DOTA_BUTTON_AREA = {"left": 1525, "top": 1005, "width": 340, "height": 55}
DESKTOP_TAB_AREA = {"left": 1750, "top": 1040, "width": 50, "height": 40}
SETTINGS_AREA = {"left": 170, "top": 85, "width": 40, "height": 40}
HERO_PICK_AREA = {"left": 1658, "top": 1028, "width": 62, "height": 38}
NEW_CAPTURE_AREA = {"left": 0, "top": 0, "width": 0, "height": 0}

DOTA_TAB_TEMPLATE = cv.imread(
    "data/opencv/pregame/dota_menu_power_icon.jpg", cv.IMREAD_GRAYSCALE
)
IN_GAME_TEMPLATE = cv.imread(
    "data/opencv/pregame/dota_courier_deliver_items_icon.jpg", cv.IMREAD_GRAYSCALE
)
STARTING_BUY_TEMPLATE = cv.imread(
    "data/opencv/pregame/dota_strategy-load-out-world-guides.jpg", cv.IMREAD_GRAYSCALE
)
PLAY_DOTA_BUTTON_TEMPLATE = cv.imread(
    "data/opencv/pregame/dota_play_dota_button.jpg", cv.IMREAD_GRAYSCALE
)
DESKTOP_TAB_TEMPLATE = cv.imread(
    "data/opencv/pregame/windows_desktop_icons.jpg", cv.IMREAD_GRAYSCALE
)
SETTINGS_TEMPLATE = cv.imread(
    "data/opencv/pregame/dota_settings_icon.jpg", cv.IMREAD_GRAYSCALE
)
HERO_PICK_TEMPLATE = cv.imread(
    "data/opencv/pregame/dota_hero_select_chat_icons.jpg", cv.IMREAD_GRAYSCALE
)

logger = utils.setup_logger(SCRIPT_NAME, logging.DEBUG)
secondary_windows_spawned = asyncio.Event()
mute_ssim_prints = asyncio.Event()


class Tabbed:
    def __init__(self):
        self._to_desktop = False
        self._to_dota_menu = False
        self._to_settings_screen = False
        self._in_game = False

    @property
    def to_desktop(self):
        return self._to_desktop

    @to_desktop.setter
    def to_desktop(self, value):
        if value:
            self._set_all_false()
        self._to_desktop = value

    @property
    def to_dota_menu(self):
        return self._to_dota_menu

    @to_dota_menu.setter
    def to_dota_menu(self, value):
        if value:
            self._set_all_false()
        self._to_dota_menu = value

    @property
    def to_settings_screen(self):
        return self._to_settings_screen

    @to_settings_screen.setter
    def to_settings_screen(self, value):
        if value:
            self._set_all_false()
        self._to_settings_screen = value

    @property
    def in_game(self):
        return self._in_game

    @in_game.setter
    def in_game(self, value):
        if value:
            self._set_all_false()
        self._in_game = value

    def _set_all_false(self):
        for attr in self.__dict__:
            if isinstance(self.__dict__[attr], bool):
                self.__dict__[attr] = False

    def current_state(self):
        if self._to_desktop:
            return "Out to desktop"
        elif self._to_dota_menu:
            return "In Dota menu"
        elif self._to_settings_screen:
            return "In settings screen"
        else:
            return "No state is True"


class PreGamePhase:

    def __init__(self):
        self._finding_game = False
        self._hero_pick = False
        self._starting_buy = False
        self._versus_screen = False
        self._in_game = False
        self._unknown = False

    @property
    def finding_game(self):
        return self._finding_game

    @finding_game.setter
    def finding_game(self, value):
        if value:
            self._set_all_false()
        self._finding_game = value

    @property
    def hero_pick(self):
        return self._hero_pick

    @hero_pick.setter
    def hero_pick(self, value):
        if value:
            self._set_all_false()
        self._hero_pick = value

    @property
    def starting_buy(self):
        return self._starting_buy

    @starting_buy.setter
    def starting_buy(self, value):
        if value:
            self._set_all_false()
        self._starting_buy = value

    @property
    def versus_screen(self):
        return self._versus_screen

    @versus_screen.setter
    def versus_screen(self, value):
        if value:
            self._set_all_false()
        self._versus_screen = value

    @property
    def in_game(self):
        return self._in_game

    @in_game.setter
    def in_game(self, value):
        if value:
            self._set_all_false()
        self._in_game = value

    @property
    def unknown(self):
        return self._unknown

    @unknown.setter
    def unknown(self, value):
        if value:
            self._set_all_false()
        self._unknown = value

    def _set_all_false(self):
        for attr in self.__dict__:
            if isinstance(self.__dict__[attr], bool):
                self.__dict__[attr] = False


class PreGamePhaseHandler(socks.BaseHandler):
    """Handler for the socket server of the script. Allows for communication
    from the server to the script."""

    def __init__(self, port, script_logger):
        super().__init__(port, script_logger)
        self.stop_event = asyncio.Event()
        self.other_event = asyncio.Event()  # Demonstrative place holder

    async def handle_message(self, message: str):
        if message == const.STOP_SUBPROCESS_MESSAGE:
            self.stop_event.set()
            self.logger.info("Socket received stop message")
        elif message == "OTHER":
            self.other_event.set()
            self.logger.info("Socket received other message")
        else:
            self.logger.info(f"Socket received: {message}")
        await self.send_ack()


async def capture_window(area: dict[str, int]):
    with mss.mss() as sct:
        img = sct.grab(area)
    return np.array(img)


async def compare_images(
    image_a: cv.typing.MatLike, image_b: cv.typing.MatLike
) -> float:
    return ssim(image_a, image_b)


async def capture_and_process_images(
    *args: tuple[int, dict, cv.typing.MatLike]
) -> dict[int, float]:
    """Compares a set of screen areas and cv2 templates between them"""
    match_values = {}

    for arg in args:
        index, capture_area, template = arg

        if capture_area is not None:
            frame = await capture_window(capture_area)
            gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

            if template is not None:
                match_value = await compare_images(gray_frame, template)
            else:
                match_value = 0.0

            if index is not None:
                window_name = SECONDARY_WINDOWS[index].name
            else:
                window_name = "Default Window"

            cv.imshow(window_name, gray_frame)

            if cv.waitKey(1) == ord("q"):
                break
            match_values[index] = match_value

    return match_values


async def detect_hero_pick():
    return await capture_and_process_images((0, HERO_PICK_AREA, HERO_PICK_TEMPLATE))


async def detect_starting_buy():
    return await capture_and_process_images(
        (1, STARTING_BUY_AREA, STARTING_BUY_TEMPLATE)
    )


async def detect_dota_tab_out():
    return await capture_and_process_images((2, DOTA_TAB_AREA, DOTA_TAB_TEMPLATE))


async def detect_desktop_tab_out():
    return await capture_and_process_images((3, DESKTOP_TAB_AREA, DESKTOP_TAB_TEMPLATE))


async def detect_settings_screen():
    return await capture_and_process_images((4, SETTINGS_AREA, SETTINGS_TEMPLATE))


async def detect_in_game():
    return await capture_and_process_images((5, IN_GAME_AREA, IN_GAME_TEMPLATE))


async def scan_screen_for_matches() -> dict[int, float]:
    (
        hero_pick_result,
        starting_buy_result,
        dota_tab_out_results,
        desktop_tab_out_results,
        settings_screens_results,
        in_game_results,
    ) = await asyncio.gather(
        detect_hero_pick(),  # index 0
        detect_starting_buy(),  # index 1
        detect_dota_tab_out(),  # index 2
        detect_desktop_tab_out(),  # index 3
        detect_settings_screen(),  # index 4
        detect_in_game(),  # index 5
    )

    secondary_windows_spawned.set()

    combined_results = {
        **hero_pick_result,
        **starting_buy_result,
        **dota_tab_out_results,
        **desktop_tab_out_results,
        **settings_screens_results,
        **in_game_results,
    }

    formatted_combined_results = ", ".join(
        [f"{index}:{value:.3f}" for index, value in combined_results.items()]
    )

    if not mute_ssim_prints.is_set():
        print(f"SSIMs: {formatted_combined_results}", end="\r")

    return combined_results


async def set_state_finding_game() -> tuple[Tabbed, PreGamePhase]:
    game_phase = PreGamePhase()
    tabbed = Tabbed()
    game_phase.finding_game = True  # initial game phase
    print("\n\n\n\n\n\n\nWaiting to find a game...")  # a few newlines to
    # make some space for reading outputs in cli below the secondary windows.
    return tabbed, game_phase


async def set_state_game_found(
    tabbed: Tabbed, game_phase: PreGamePhase, ws: WebSocketClientProtocol
) -> tuple[Tabbed, PreGamePhase]:
    tabbed.in_game = True
    game_phase.hero_pick = True
    print("\nFound a game !")

    await websocket.send_json_requests(
        ws, "data/ws_requests/pregame/scene_change_in_game.json", logger
    )
    return tabbed, game_phase


async def set_state_hero_pick(
    tabbed: Tabbed, game_phase: PreGamePhase, ws: WebSocketClientProtocol
) -> tuple[Tabbed, PreGamePhase]:
    tabbed.in_game = True
    game_phase.hero_pick = True
    print("\nBack to hero select !")

    await websocket.send_json_requests(
        ws, "data/ws_requests/pregame/scene_change_dslr_move_hero_pick.json"
    )
    return tabbed, game_phase


async def set_state_starting_buy(
    tabbed: Tabbed, game_phase: PreGamePhase, ws: WebSocketClientProtocol
) -> tuple[Tabbed, PreGamePhase]:
    tabbed.in_game = True
    game_phase.starting_buy = True
    print("\nStarting buy !")

    await websocket.send_json_requests(
        ws, "data/ws_requests/pregame/dslr_move_starting_buy.json", logger
    )
    return tabbed, game_phase


async def set_state_vs_screen(
    tabbed: Tabbed, game_phase: PreGamePhase, ws: WebSocketClientProtocol
) -> tuple[Tabbed, PreGamePhase]:
    tabbed.in_game = True
    game_phase.versus_screen = True

    await websocket.send_json_requests(
        ws, "data/ws_requests/pregame/dslr_hide_vs_screen.json", logger
    )
    print("\nWe are in vs screen !")
    return tabbed, game_phase


async def set_state_in_game(
    tabbed: Tabbed, game_phase: PreGamePhase, ws: WebSocketClientProtocol
) -> tuple[Tabbed, PreGamePhase]:
    tabbed.in_game = True
    game_phase.in_game = True

    await websocket.send_json_requests(
        ws, "data/ws_requests/pregame/scene_change_in_game.json", logger
    )
    print("\nWe are in now game !")
    return tabbed, game_phase


async def set_state_dota_menu(
    tabbed: Tabbed, game_phase: PreGamePhase, ws: WebSocketClientProtocol
) -> tuple[Tabbed, PreGamePhase]:
    tabbed.to_dota_menu = True
    game_phase.unknown = True

    await websocket.send_json_requests(
        ws, "data/ws_requests/pregame/dslr_hide_vs_screen.json", logger
    )
    print("\nWe are in Dota Menus !")
    return tabbed, game_phase


async def set_state_desktop(
    tabbed: Tabbed, game_phase: PreGamePhase
) -> tuple[Tabbed, PreGamePhase]:
    tabbed.to_desktop = True
    game_phase.unknown = True
    print("\nWe are on desktop !")
    return tabbed, game_phase


async def set_state_settings_screen(
    tabbed: Tabbed, game_phase: PreGamePhase, ws: WebSocketClientProtocol
) -> tuple[Tabbed, PreGamePhase]:
    tabbed.to_settings_screen = True
    game_phase.unknown = True

    await websocket.send_json_requests(
        ws, "data/ws_requests/pregame/dslr_hide_vs_screen.json", logger
    )
    print("\nWe are in settings !")
    return tabbed, game_phase


async def confirm_transition_to_vs_screen(
    tabbed: Tabbed,
    game_phase: PreGamePhase,
    target_value: float,
    ws: WebSocketClientProtocol,
) -> tuple[Tabbed, PreGamePhase]:
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
            f"Checking for vs screen... " f"({time.time() - start_time:.4f}s elapsed.)",
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
    game_phase: PreGamePhase,
) -> PreGamePhase:
    """Delay to allow time for the starting buy screen fade out when
    transitioning to the hero select or settings screen. Does not trigger
    if tabbing out to Dota or Desktop since in the progressive fade from
    starting buy screen does not occur."""
    game_phase.starting_buy = False
    await asyncio.sleep(0.25)
    return game_phase


async def capture_new_area(capture_area: dict[str, int], filename: str):
    frame = await capture_window(capture_area)
    gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    cv.imshow("new_area_capture", gray_frame)
    secondary_windows_spawned.set()
    cv.imwrite(filename, gray_frame)


async def detect_pregame_phase(
    ws: WebSocketClientProtocol, socket_handler: PreGamePhaseHandler
):
    #  ----------- The code below is not part of the main logic ------------
    new_capture = False  # Set manually to capture new screen area
    while new_capture:
        await capture_new_area(NEW_CAPTURE_AREA, "opencv/XXX.jpg")
    #  ----------- The code above is not part of the main logic ------------

    tabbed, game_phase = await set_state_finding_game()
    target = 0.7  # target value for ssim
    while not socket_handler.stop_event.is_set():

        ssim_match = await scan_screen_for_matches()

        if (
            tabbed.to_settings_screen
            and ssim_match[4] < target
            and not ssim_match[3] >= target
        ):
            tabbed = await wait_for_settings_screen_fade_out(tabbed)
            continue

        if (
            game_phase.starting_buy
            and ssim_match[1] < target
            and not ssim_match[2] >= target
            and not ssim_match[3] >= target
        ):
            game_phase = await wait_for_starting_buy_screen_fade_out(game_phase)
            continue

        if ssim_match[0] >= target and game_phase.finding_game:
            tabbed, game_phase = await set_state_game_found(tabbed, game_phase, ws)
            continue

        if not game_phase.finding_game:

            if ssim_match[1] >= target and not game_phase.starting_buy:
                tabbed, game_phase = await set_state_starting_buy(
                    tabbed, game_phase, ws
                )
                continue

            if (
                ssim_match[0] >= target > ssim_match[1]
                and ssim_match[4] < target
                and ssim_match[3] < target
                and not game_phase.hero_pick
            ):
                tabbed, game_phase = await set_state_hero_pick(tabbed, game_phase, ws)
                continue

            if ssim_match[2] >= target and not tabbed.to_dota_menu:
                tabbed, game_phase = await set_state_dota_menu(tabbed, game_phase, ws)
                continue

            if ssim_match[3] >= target and not tabbed.to_desktop:
                tabbed, game_phase = await set_state_desktop(tabbed, game_phase)
                continue

            if ssim_match[4] >= target and not tabbed.to_settings_screen:
                tabbed, game_phase = await set_state_settings_screen(
                    tabbed, game_phase, ws
                )
                continue

            if ssim_match[5] >= target and not game_phase.in_game:
                tabbed, game_phase = await set_state_in_game(tabbed, game_phase, ws)
                continue

            if max(ssim_match.values()) < target and not game_phase.versus_screen:
                tabbed, game_phase = await confirm_transition_to_vs_screen(
                    tabbed, game_phase, target, ws
                )
                continue

        await asyncio.sleep(0.01)


async def run_main_task(
    slot: int, socket_handler: PreGamePhaseHandler, ws: WebSocketClientProtocol
):
    mute_ssim_prints.set()
    main_task = asyncio.create_task(detect_pregame_phase(ws, socket_handler))

    await secondary_windows_spawned.wait()
    await twm.manage_secondary_windows(slot, SECONDARY_WINDOWS)
    mute_ssim_prints.clear()
    await main_task
    return None


async def main():
    db_conn = None
    ws = None
    socket_server_task = None

    try:
        lfm = utils.LockFileManager(SCRIPT_NAME)
        db_conn = await sdh.create_connection(DB)

        if lfm.lock_exists():
            await setup_script_basics(db_conn, WinType.DENIED, SCRIPT_NAME)
        else:
            slot, name = await setup_script_basics(
                db_conn, WinType.ACCEPTED, SCRIPT_NAME, lfm, SECONDARY_WINDOWS
            )
            socket_server_handler = PreGamePhaseHandler(PORT, logger)
            socket_server_task = asyncio.create_task(
                socket_server_handler.run_socket_server()
            )

            ws = await websocket.establish_ws_connection(URL, logger)
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
        if db_conn:
            await db_conn.close()
        cv.destroyAllWindows()


if __name__ == "__main__":
    asyncio.run(main())
    utils.countdown()
