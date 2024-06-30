import atexit
import aiosqlite
import cv2
import cv2 as cv
import mss
import numpy as np
from skimage.metrics import structural_similarity as ssim
import asyncio
import my_classes as my
import my_utils
import single_instance
import terminal_window_manager_v4 as twm
import denied_slots_db_handler as denied_sdh
import slots_db_handler as sdh
import websockets
from websockets import WebSocketException, ConnectionClosedError
import constants as const
import logging
from enum import Enum, auto
import time


class InterruptType(Enum):
    DOTA_TAB_OUT = auto()
    DESKTOP_TAB_OUT = auto()
    GAME_CANCEL = auto()
    SETTINGS_SCREEN = auto()
    VERSUS_SCREEN = auto()
    TRANSITION_MESSAGE = auto()


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
        self._to_desktop = False
        self._to_dota_menu = False
        self._to_settings_screen = False
        self._in_game = False

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
        self._finding_game = False
        self._hero_pick = False
        self._starting_buy = False
        self._versus_screen = False
        self._in_game = False


DOTA_TAB_AREA = {"left": 1860, "top": 10, "width": 60, "height": 40}
STARTING_BUY_AREA = {"left": 860, "top": 120, "width": 400, "height": 30}
IN_GAME_AREA = {"left": 1820, "top": 1020, "width": 80, "height": 60}
PLAY_DOTA_BUTTON_AREA = {"left": 1525, "top": 1005, "width": 340, "height": 55}
DESKTOP_TAB_AREA = {"left": 1750, "top": 1040, "width": 50, "height": 40}
SETTINGS_AREA = {"left": 170, "top": 85, "width": 40, "height": 40}
HERO_PICK_AREA = {"left": 1658, "top": 1028, "width": 62, "height": 38}
NEW_AREA = {"left": 0, "top": 0, "width": 0, "height": 0}

DOTA_TAB_TEMPLATE = cv2.imread("opencv/dota_power_icon.jpg",
                               cv.IMREAD_GRAYSCALE)
IN_GAME_TEMPLATE = cv2.imread("opencv/deliver_items_icon.jpg",
                              cv.IMREAD_GRAYSCALE)
STARTING_BUY_TEMPLATE = cv2.imread("opencv/strategy-load-out-world-guides.jpg",
                                   cv.IMREAD_GRAYSCALE)
PLAY_DOTA_BUTTON_TEMPLATE = cv2.imread("opencv/play_dota.jpg",
                                       cv.IMREAD_GRAYSCALE)
DESKTOP_TAB_TEMPLATE = cv2.imread("opencv/desktop_icons.jpg",
                                  cv.IMREAD_GRAYSCALE)
SETTINGS_TEMPLATE = cv2.imread("opencv/dota_settings_icon.jpg",
                               cv.IMREAD_GRAYSCALE)
HERO_PICK_TEMPLATE = cv2.imread("opencv/hero_pick_chat_icons.jpg",
                                cv.IMREAD_GRAYSCALE)

SECONDARY_WINDOWS = [my.SecondaryWindow("first_scanner", 150, 80),
                     my.SecondaryWindow("second_scanner", 150, 80),
                     my.SecondaryWindow("third_scanner", 150, 80),
                     my.SecondaryWindow("fourth_scanner", 150, 80),
                     my.SecondaryWindow("fifth_scanner", 150, 80),
                     my.SecondaryWindow("sixth_scanner", 150, 100)]
SCRIPT_NAME = my_utils.construct_script_name(__file__,
                                             const.SCRIPT_NAME_SUFFIX)
# suffix added to avoid window naming conflicts with cli manager
STREAMERBOT_WS_URL = "ws://127.0.0.1:50001/"

logger = my_utils.setup_logger(SCRIPT_NAME, logging.DEBUG)
last_log_time = time.time()

initial_secondary_windows_spawned = asyncio.Event()
secondary_windows_readjusted = asyncio.Event()
mute_ssim_prints = asyncio.Event()
stop_event = asyncio.Event()


async def establish_ws_connection():
    try:
        ws = await websockets.connect(STREAMERBOT_WS_URL)
        logger.info(f"Established connection: {ws}")
        return ws
    except WebSocketException as e:
        logger.debug(f"Websocket error: {e}")
    except OSError as e:
        logger.debug(f"OS error: {e}")
    return None


async def handle_socket_client(reader, writer):
    while True:
        data = await reader.read(1024)
        if not data:
            print("Socket client disconnected")
            break
        message = data.decode()
        if message == const.STOP_SUBPROCESS_MESSAGE:
            stop_event.set()
        print(f"Received: {message}")
        writer.write(b"ACK from WebSocket server")
        await writer.drain()
    writer.close()


async def run_socket_server():
    logger.info("Starting script socket server")
    server = await asyncio.start_server(handle_socket_client, 'localhost',
                                        const.SUBPROCESSES[SCRIPT_NAME])
    addr = server.sockets[0].getsockname()
    print(f"Serving on {addr}")
    logger.info(f"Serving on {addr}")

    try:
        await server.serve_forever()
    except asyncio.CancelledError:
        print("Socket server task was cancelled. Stopping server")
    finally:
        server.close()
        await server.wait_closed()
        print("Server closed")


async def capture_window(area: dict[str, int]):
    with mss.mss() as sct:
        img = sct.grab(area)
    return np.array(img)


async def compare_images(image_a, image_b):
    return ssim(image_a, image_b)


async def send_json_requests(ws: websockets.WebSocketClientProtocol,
                             json_file_paths: str | list[str]):
    if isinstance(json_file_paths, str):
        json_file_paths = [json_file_paths]

    for json_file in json_file_paths:
        try:
            with open(json_file, 'r') as file:
                await ws.send(file.read())
            response = await ws.recv()
            logger.info(f"WebSocket response: {response}")
        except ConnectionClosedError as e:
            logger.error(f"WebSocket connection closed: {e}")
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")


async def send_streamerbot_ws_request(tabbed: Tabbed, game_phase: PreGamePhase,
                                      ws: websockets.WebSocketClientProtocol):
    if tabbed.in_game:
        pass
    elif tabbed.to_dota_menu:
        pass
    elif tabbed.to_desktop:
        pass
    elif tabbed.to_settings_screen:
        await send_json_requests(
            ws, "streamerbot_ws_requests/pregame_dslr_hide_for_vs_screen.json")

    elif game_phase.finding_game:
        await send_json_requests(
            ws,
            "streamerbot_ws_requests/pregame_scene_change_for_in_game.json")
    elif game_phase.hero_pick:
        await send_json_requests(
            ws, "streamerbot_ws_requests/"
                "pregame_scene_change_dslr_move_for_hero_pick.json")
    elif game_phase.starting_buy:
        await send_json_requests(
            ws,
            "streamerbot_ws_requests/pregame_dslr_move_for_starting_buy.json")
    elif game_phase.versus_screen:
        await send_json_requests(
            ws, "streamerbot_ws_requests/pregame_dslr_hide_for_vs_screen.json")
    elif game_phase.in_game:
        await send_json_requests(
            ws,
            "streamerbot_ws_requests/pregame_scene_change_for_in_game.json")
    elif game_phase.unknown:
        pass


async def readjust_secondary_windows(conn: aiosqlite.Connection):
    sdh_slot = await sdh.get_slot_by_main_name(conn, SCRIPT_NAME)
    logger.debug(f"Obtained slot from db is {sdh_slot}. Resizing "
                 f"secondary windows ")
    await twm.manage_secondary_windows(sdh_slot, SECONDARY_WINDOWS)


async def match_interrupt_template(area: dict[str, int],
                                   template: cv.typing.MatLike):
    frame = await capture_window(area)
    gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    cv.imshow(SECONDARY_WINDOWS[2].name, gray_frame)
    match_value = await compare_images(gray_frame, template)
    return match_value


async def capture_and_process_images(
        *args: tuple[int, dict, cv.typing.MatLike]) -> dict[int, float]:
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
    return await capture_and_process_images(
        (0, HERO_PICK_AREA, HERO_PICK_TEMPLATE))


async def detect_starting_buy():
    return await capture_and_process_images(
        (1, STARTING_BUY_AREA, STARTING_BUY_TEMPLATE))


async def detect_dota_tab_out():
    return await capture_and_process_images(
        (2, DOTA_TAB_AREA, DOTA_TAB_TEMPLATE))


async def detect_desktop_tab_out():
    return await capture_and_process_images(
        (3, DESKTOP_TAB_AREA, DESKTOP_TAB_TEMPLATE))


async def detect_settings_screen():
    return await capture_and_process_images(
        (4, SETTINGS_AREA, SETTINGS_TEMPLATE))


async def detect_vs_screen():
    vs_screen_match = await capture_and_process_images(
        (0, HERO_PICK_AREA, HERO_PICK_TEMPLATE),
        (1, SETTINGS_AREA, SETTINGS_TEMPLATE),
        (2, DOTA_TAB_AREA, DOTA_TAB_TEMPLATE),
        (3, DESKTOP_TAB_AREA, DESKTOP_TAB_TEMPLATE))
    return True if max(vs_screen_match) < 0.7 else False


async def detect_in_game():
    return await capture_and_process_images(
        (5, IN_GAME_AREA, IN_GAME_TEMPLATE))


async def wait_for_duration(duration: float):
    start_time = time.time()
    while time.time() - start_time < duration:
        elapsed_time = time.time() - start_time
        percentage = (elapsed_time / duration) * 100
        print(f"Waiting {duration}s... {percentage:.2f}%", end='\r')


async def scan_screen_for_matches() -> dict[int:float]:
    global last_log_time
    (hero_pick_result, starting_buy_result, dota_tab_out_results,
     desktop_tab_out_results, settings_screens_results, in_game_results) \
        = await (
        asyncio.gather(
            detect_hero_pick(),  # index 0
            detect_starting_buy(),  # index 1
            detect_dota_tab_out(),  # index 2
            detect_desktop_tab_out(),  # index 3
            detect_settings_screen(),  # index 4
            detect_in_game()  # index 5
        ))

    initial_secondary_windows_spawned.set()

    combined_results = {**hero_pick_result, **starting_buy_result,
                        **dota_tab_out_results, **desktop_tab_out_results,
                        **settings_screens_results, **in_game_results}

    if time.time() - last_log_time > 1:
        # Only log every 1s
        logger.debug(f"combined_results ={combined_results}")
        last_log_time = time.time()

    formatted_combined_results = ", ".join(
        [f"{index}:{value:.3f}" for
         index, value in combined_results.items()])

    if not mute_ssim_prints.is_set():
        print(f"SSIMs: {formatted_combined_results}", end='\r')

    return combined_results


async def set_state_finding_game() -> tuple[Tabbed, PreGamePhase, float]:
    game_phase = PreGamePhase()
    tabbed = Tabbed()
    target_match_value_for_ssim = 0.7
    game_phase.finding_game = True  # initial game phase
    print("\n\n\n\n\n\n\nWaiting to find a game...")  # a few newlines to
    # make some space for reading outputs in cli below the secondary windows.
    return tabbed, game_phase, target_match_value_for_ssim


async def set_state_game_found(tabbed: Tabbed, game_phase: PreGamePhase,
                               ws: websockets.WebSocketClientProtocol) \
        -> tuple[Tabbed, PreGamePhase]:
    tabbed.in_game = True
    game_phase.hero_pick = True
    print("\nFound a game !")
    await send_streamerbot_ws_request(tabbed, game_phase, ws)
    return tabbed, game_phase


async def set_state_hero_pick(tabbed: Tabbed, game_phase: PreGamePhase,
                              ws: websockets.WebSocketClientProtocol) \
        -> tuple[Tabbed, PreGamePhase]:
    tabbed.in_game = True
    game_phase.hero_pick = True
    print("\nBack to hero select !")
    await send_streamerbot_ws_request(tabbed, game_phase, ws)
    return tabbed, game_phase


async def set_state_starting_buy(tabbed: Tabbed, game_phase: PreGamePhase,
                                 ws: websockets.WebSocketClientProtocol) \
        -> tuple[Tabbed, PreGamePhase]:
    tabbed.in_game = True
    game_phase.starting_buy = True
    print("\nStarting buy !")
    await send_streamerbot_ws_request(tabbed, game_phase, ws)
    return tabbed, game_phase


async def set_state_vs_screen(tabbed: Tabbed, game_phase: PreGamePhase,
                              ws: websockets.WebSocketClientProtocol) \
        -> tuple[Tabbed, PreGamePhase]:
    tabbed.in_game = True
    game_phase.versus_screen = True
    print("\nWe are in vs screen !")
    await send_streamerbot_ws_request(tabbed, game_phase, ws)
    return tabbed, game_phase


async def set_state_in_game(tabbed: Tabbed, game_phase: PreGamePhase,
                            ws: websockets.WebSocketClientProtocol) \
        -> tuple[Tabbed, PreGamePhase]:
    tabbed.in_game = True
    game_phase.in_game = True
    print("\nWe are in now game !")
    await send_streamerbot_ws_request(tabbed, game_phase, ws)
    return tabbed, game_phase


async def set_state_dota_menu(tabbed: Tabbed, game_phase: PreGamePhase,
                              ws: websockets.WebSocketClientProtocol) \
        -> tuple[Tabbed, PreGamePhase]:
    tabbed.to_dota_menu = True
    game_phase.unknown = True
    print("\nWe are in Dota Menus !")
    await send_streamerbot_ws_request(tabbed, game_phase, ws)
    return tabbed, game_phase


async def set_state_desktop(tabbed: Tabbed, game_phase: PreGamePhase,
                            ws: websockets.WebSocketClientProtocol) \
        -> tuple[Tabbed, PreGamePhase]:
    tabbed.to_desktop = True
    game_phase.unknown = True
    print("\nWe are on desktop !")
    await send_streamerbot_ws_request(tabbed, game_phase, ws)
    return tabbed, game_phase


async def set_state_settings_screen(
        tabbed: Tabbed, game_phase: PreGamePhase,
        ws: websockets.WebSocketClientProtocol) \
        -> tuple[Tabbed, PreGamePhase]:
    tabbed.to_settings_screen = True
    game_phase.unknown = True
    print("\nWe are in settings !")
    await send_streamerbot_ws_request(tabbed, game_phase, ws)
    return tabbed, game_phase


async def confirm_transition_to_vs_screen(
        tabbed: Tabbed, game_phase: PreGamePhase, target_value: float,
        ws: websockets.WebSocketClientProtocol) -> tuple[Tabbed, PreGamePhase]:
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
        print(f"Checking for vs screen... "
              f"({time.time() - start_time:.4f}s elapsed.)", end='\r')
        ssim_match = await scan_screen_for_matches()

        if max(ssim_match.values()) >= target:
            print("\nNot in vs screen !")
            break
        elif time.time() - start_time >= duration:
            # The condition was true for the entire 0.5 seconds
            tabbed, game_phase = await set_state_vs_screen(tabbed,
                                                           game_phase, ws)
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


async def wait_for_starting_buy_screen_fade_out(game_phase: PreGamePhase) \
        -> PreGamePhase:
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
    initial_secondary_windows_spawned.set()
    cv.imwrite(filename, gray_frame)


async def detect_pregame_phase(ws: websockets.WebSocketClientProtocol):
    #  ----------- The code below is not part of the main logic ------------
    new_capture = False  # Set manually to capture new screen area
    while new_capture:
        await capture_new_area(NEW_AREA, "opencv/XXX.jpg")
    #  ----------- The code above is not part of the main logic ------------

    tabbed, game_phase, target = await set_state_finding_game()

    while not stop_event.is_set():

        ssim_match = await scan_screen_for_matches()

        if (tabbed.to_settings_screen
                and ssim_match[4] < target
                and not ssim_match[3] >= target):
            tabbed = await wait_for_settings_screen_fade_out(tabbed)
            continue

        if (game_phase.starting_buy
                and ssim_match[1] < target
                and not ssim_match[2] >= target
                and not ssim_match[3] >= target):
            game_phase = await (
                wait_for_starting_buy_screen_fade_out(game_phase))
            continue

        if ssim_match[0] >= target and game_phase.finding_game:
            tabbed, game_phase = await (
                set_state_game_found(tabbed, game_phase, ws))
            continue

        if not game_phase.finding_game:

            if ssim_match[1] >= target and not game_phase.starting_buy:
                tabbed, game_phase = await (
                    set_state_starting_buy(tabbed, game_phase, ws))
                continue

            if (ssim_match[0] >= target > ssim_match[1]
                    and ssim_match[4] < target
                    and ssim_match[3] < target
                    and not game_phase.hero_pick):
                tabbed, game_phase = await (
                    set_state_hero_pick(tabbed, game_phase, ws))
                continue

            if ssim_match[2] >= target and not tabbed.to_dota_menu:
                tabbed, game_phase = await (
                    set_state_dota_menu(tabbed, game_phase, ws))
                continue

            if ssim_match[3] >= target and not tabbed.to_desktop:
                tabbed, game_phase = await (
                    set_state_desktop(tabbed, game_phase, ws))
                continue

            if ssim_match[4] >= target and not tabbed.to_settings_screen:
                tabbed, game_phase = await (
                    set_state_settings_screen(tabbed, game_phase, ws))
                continue

            if ssim_match[5] >= target and not game_phase.in_game:
                tabbed, game_phase = await (
                    set_state_in_game(tabbed, game_phase, ws))
                continue

            if (max(ssim_match.values()) < target
                    and not game_phase.versus_screen):
                tabbed, game_phase = await (confirm_transition_to_vs_screen(
                    tabbed, game_phase, target, ws))
                continue

        await asyncio.sleep(0.01)


async def main():
    db_conn = None
    try:
        db_conn = await sdh.create_connection(const.SLOTS_DB_FILE)
        if single_instance.lock_exists(SCRIPT_NAME):
            slot = await twm.manage_window(db_conn, twm.WinType.DENIED,
                                           SCRIPT_NAME)
            atexit.register(denied_sdh.free_slot_sync, slot)
            print("\n>>> Lock file is present: exiting... <<<")
        else:
            mute_ssim_prints.set()
            slot = await twm.manage_window(db_conn, twm.WinType.ACCEPTED,
                                           SCRIPT_NAME, SECONDARY_WINDOWS)
            single_instance.create_lock_file(SCRIPT_NAME)
            atexit.register(single_instance.remove_lock, SCRIPT_NAME)
            atexit.register(sdh.free_slot_by_name_sync, SCRIPT_NAME)
            socket_server_task = asyncio.create_task(run_socket_server())
            ws = None
            try:
                ws = await establish_ws_connection()
                main_task = asyncio.create_task(detect_pregame_phase(ws))
                await initial_secondary_windows_spawned.wait()
                await twm.manage_secondary_windows(slot, SECONDARY_WINDOWS)
                mute_ssim_prints.clear()
                await main_task
            except KeyboardInterrupt:
                print("KeyboardInterrupt")
            finally:
                socket_server_task.cancel()
                await socket_server_task
                await db_conn.close()
                cv.destroyAllWindows()
                if ws:
                    await ws.close()
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise
    finally:
        if db_conn:
            await db_conn.close()


if __name__ == "__main__":
    asyncio.run(main())
    twm.window_exit_countdown(5)
