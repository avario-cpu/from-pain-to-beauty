import atexit
import os

import cv2
import cv2 as cv
import mss
import numpy as np
from skimage.metrics import structural_similarity as ssim
import asyncio
import my_classes as my
import single_instance
import terminal_window_manager_v4 as twm
import denied_slots_db_handler as denied_sdh
import slots_db_handler as sdh
import websockets
from websockets import WebSocketException, ConnectionClosedError
import constants
import logging
import time
from enum import Enum, auto


class PreGamePhases:

    def __init__(self):
        self._finding_game = False
        self._hero_pick = False
        self._starting_buy = False
        self._versus_screen = False
        self._in_game = False

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

    def _set_all_false(self):
        self._finding_game = False
        self._hero_pick = False
        self._starting_buy = False
        self._versus_screen = False
        self._in_game = False

    def __str__(self):

        return (
            f"finding_game: {self._finding_game}, hero_pick: {self._hero_pick}"
            f", starting_buy: {self._starting_buy}, versus_screen: "
            f"{self._versus_screen}, in_game: {self._in_game}")


class InterruptType(Enum):
    TAB_OUT = auto()
    EXIT = auto()
    GAME_CANCELED = auto()
    DRAFT_SCREEN_CHANGE = auto()
    START_BUY_SCREEN = auto()
    SETTINGS_SCREEN = auto()
    VERSUS_SCREEN = auto()


PICK_PHASE_TIMER_AREA = {"left": 880, "top": 70, "width": 160, "height": 30}
STARTING_BUY_AREA = {"left": 860, "top": 120, "width": 400, "height": 30}
IN_GAME_AREA = {"left": 1820, "top": 1020, "width": 80, "height": 60}
DOTA_SETTINGS_AREA = {"left": 60, "top": 10, "width": 40, "height": 40}
PLAY_DOTA_BUTTON_AREA = {"left": 1525, "top": 1005, "width": 340,
                         "height": 55}
POWER_ICON_AREA = {"left": 1860, "top": 10, "width": 60, "height": 40}

ALL_PICK_TEMPLATE = cv2.imread("../opencv/all_pick.jpg", cv.IMREAD_GRAYSCALE)
STRATEGY_TIME_TEMPLATE = cv2.imread("../opencv/strategy_time.jpg",
                                    cv.IMREAD_GRAYSCALE)
STARTING_BUY_TEMPLATE = cv2.imread(
    "../opencv/strategy-load-out-world-guides.jpg",
    cv.IMREAD_GRAYSCALE)
IN_GAME_TEMPLATE = cv2.imread("../opencv/deliver_items_icon.jpg",
                              cv.IMREAD_GRAYSCALE)
PLAY_DOTA_BUTTON_TEMPLATE = cv2.imread("../opencv/play_dota.jpg",
                                       cv.IMREAD_GRAYSCALE)

POWER_ICON_TEMPLATE = cv2.imread("../opencv/dota_power_icon.jpg",
                                 cv.IMREAD_GRAYSCALE)

SECONDARY_WINDOWS = [my.SecondaryWindow("opencv_hero_pick_scanner", 400, 100)]
SCRIPT_NAME = constants.SCRIPT_NAME_SUFFIX + os.path.splitext(
    os.path.basename(__file__))[0] if __name__ == "__main__" else __name__
# suffix added to avoid window naming conflicts with cli manager
STREAMERBOT_WS_URL = "ws://127.0.0.1:50001/"

secondary_windows_have_spawned = asyncio.Event()
mute_main_loop_print_feedback = asyncio.Event()
stop_main_loop = asyncio.Event()

logger = logging.getLogger(SCRIPT_NAME)
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(f'temp/logs/{SCRIPT_NAME}.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


def exit_countdown():
    """Give a bit of time to read terminal exit statements"""
    for seconds in reversed(range(1, 5)):
        print("\r" + f'cmd will close in {seconds} seconds...', end="\r")
        time.sleep(1)
    exit()


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
        if message == constants.STOP_SUBPROCESS_MESSAGE:
            stop_main_loop.set()
        print(f"Received: {message}")
        writer.write(b"ACK from WebSocket server")
        await writer.drain()
    writer.close()


async def run_socket_server():
    logger.info("Starting run_socket_server")
    server = await asyncio.start_server(handle_socket_client, 'localhost',
                                        constants.SUBPROCESSES[SCRIPT_NAME])
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


async def capture_window(area):
    with mss.mss() as sct:
        img = sct.grab(area)
    return np.array(img)


async def compare_images(image_a, image_b):
    return ssim(image_a, image_b)


async def send_json_requests(ws, json_file_paths: str | list[str]):
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


async def send_streamerbot_ws_request(ws, game_phase):
    if game_phase.in_game:
        await send_json_requests(
            ws,
            "../streamerbot_ws_requests/pregame_scene_change_for_in_game.json")
    elif game_phase.versus_screen:
        await send_json_requests(
            ws,
            "../streamerbot_ws_requests/pregame_dslr_hide_for_vs_screen.json")
    elif game_phase.starting_buy:
        await send_json_requests(
            ws,
            "../streamerbot_ws_requests/pregame_dslr_move_for_starting_buy.json")
    elif game_phase.hero_pick:
        await send_json_requests(
            ws,
            "../streamerbot_ws_requests/pregame_scene_change_dslr_move_for_hero_pick.json")
    elif game_phase.finding_game:
        await send_json_requests(
            ws,
            "../streamerbot_ws_requests/pregame_scene_change_for_in_game.json")


async def capture_and_process_image(capture_area,
                                    template: cv2.typing.MatLike):
    frame = await capture_window(capture_area)
    gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    match_value = await compare_images(gray_frame, template)
    cv.imshow(SECONDARY_WINDOWS[0].name, gray_frame)
    secondary_windows_have_spawned.set()
    return match_value


async def capture_new_area(capture_area, filename):
    frame = await capture_window(capture_area)
    gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    cv.imshow(SECONDARY_WINDOWS[0].name, gray_frame)
    secondary_windows_have_spawned.set()
    cv.imwrite(filename, gray_frame)


async def define_relevant_match(game_phase: PreGamePhases):
    capture_area = None
    template = None
    if game_phase.in_game:
        pass
    elif game_phase.versus_screen:
        capture_area = IN_GAME_AREA
        template = IN_GAME_TEMPLATE
    elif game_phase.starting_buy or game_phase.hero_pick:
        capture_area = STARTING_BUY_AREA
        template = STARTING_BUY_TEMPLATE
    elif game_phase.finding_game:
        capture_area = PICK_PHASE_TIMER_AREA
        template = ALL_PICK_TEMPLATE
    return capture_area, template


async def analyze_dota_interrupt(game_phase):
    # Check if "Return to game" button shows

    async def check_for_tab_out():
        if game_phase.hero_pick or game_phase.starting_buy:
            match_value = await capture_and_process_image(POWER_ICON_AREA,
                                                          POWER_ICON_TEMPLATE)
            logger.debug(f"Tab-out check: match_value={match_value}")
            if match_value >= 0.8:
                logger.debug(f"High TABOUT match value !!")
            return InterruptType.TAB_OUT if match_value >= 0.8 else None

    async def check_for_draft_screen_change():
        if game_phase.starting_buy:
            match_value_all_pick = await capture_and_process_image(
                PICK_PHASE_TIMER_AREA, ALL_PICK_TEMPLATE)
            match_value_strategy_time = await capture_and_process_image(
                PICK_PHASE_TIMER_AREA, STRATEGY_TIME_TEMPLATE)
            if match_value_all_pick >= 0.8 or match_value_strategy_time >= 0.8:
                return InterruptType.DRAFT_SCREEN_CHANGE
        return None

    async def check_for_game_cancel():
        if game_phase.hero_pick or game_phase.starting_buy:
            match_value = await capture_and_process_image(
                PLAY_DOTA_BUTTON_AREA, PLAY_DOTA_BUTTON_TEMPLATE)
            return InterruptType.GAME_CANCELED if match_value >= 0.8 else None

    async def check_for_vs_screen():
        if game_phase.hero_pick or game_phase.starting_buy:
            match_value_all_pick = await capture_and_process_image(
                PICK_PHASE_TIMER_AREA, ALL_PICK_TEMPLATE)
            match_value_strategy_time = await capture_and_process_image(
                PICK_PHASE_TIMER_AREA, STRATEGY_TIME_TEMPLATE)
            if (match_value_all_pick <= 0.8 and
                    match_value_strategy_time <= 0.8):
                return InterruptType.VERSUS_SCREEN
            return None

    initial_results = await asyncio.gather(
        check_for_tab_out(),
        check_for_draft_screen_change(),
        check_for_game_cancel()
    )

    for result in initial_results:
        if result:
            return result

    vs_screen_result = await check_for_vs_screen()
    if vs_screen_result:
        await asyncio.sleep(0.3)
        # Check again after a short delay, to ensure the "vs screen" detection
        # isn't due to some short visual glitch/black out.
        initial_results_recheck = await asyncio.gather(
            check_for_tab_out(),
            check_for_draft_screen_change(),
            check_for_game_cancel()
        )
        for result in initial_results_recheck:
            if result:
                return result

        return vs_screen_result

    return None


async def pause_detection(ws, game_phase):
    if await analyze_dota_interrupt(game_phase) == InterruptType.TAB_OUT:
        print("You tabbed out, in Dota")
        while True:
            # Keep looping as long as "Disconnect" button shows up
            match_value = await capture_and_process_image(
                POWER_ICON_AREA, POWER_ICON_TEMPLATE)
            if match_value <= 0.8:
                print("exited Dota tab out")
                break

    elif await analyze_dota_interrupt(
            game_phase) == InterruptType.DRAFT_SCREEN_CHANGE:
        print("You swiped back to hero pick screen")
        # Fictional delay of 300ms to match animation...
        await asyncio.sleep(0.3)
        game_phase.hero_pick = True
        await send_streamerbot_ws_request(ws, game_phase)
        capture_area, template = await define_relevant_match(game_phase)
        return capture_area, template, game_phase

    elif await analyze_dota_interrupt(
            game_phase) == InterruptType.GAME_CANCELED:
        print("Your game got canceled ! Resetting the script.")
        game_phase.finding_game = True
        await send_streamerbot_ws_request(ws, game_phase)
        capture_area, template = await define_relevant_match(
            game_phase)
        return capture_area, template, game_phase

    elif await analyze_dota_interrupt(
            game_phase) == InterruptType.VERSUS_SCREEN:
        print("You're in VS screen, or left Dota")
        game_phase.versus_screen = True
        await send_streamerbot_ws_request(ws, game_phase)
        capture_area, template = await define_relevant_match(
            game_phase)
        return capture_area, template, game_phase

    capture_area, template = await define_relevant_match(game_phase)
    return capture_area, template, game_phase


async def detect_pregame_phase(ws):
    game_phase = PreGamePhases()
    game_phase.finding_game = True
    capture_area, template = await define_relevant_match(game_phase)

    while not stop_main_loop.is_set():

        match_value = await capture_and_process_image(capture_area, template)
        # match_value = 0.7
        # await capture_new_area(DOTA_PLUS_BUTTONS_AREA,
        #                        "opencv/dota_power_icon.jpg")

        if cv.waitKey(1) == ord("q"):
            break
        if not mute_main_loop_print_feedback.is_set():
            print(f"SSIM: {match_value:.6f}", end="\r")

        if match_value >= 0.8 and game_phase.finding_game:
            print("On hero pick screen")
            game_phase.hero_pick = True
            await send_streamerbot_ws_request(ws, game_phase)
            capture_area, template = await define_relevant_match(game_phase)
            continue

        elif match_value <= 0.8 and game_phase.hero_pick:
            capture_area, template, game_phase = \
                await pause_detection(ws, game_phase)
            continue

        elif match_value >= 0.8 and game_phase.hero_pick:
            print("Now, this is the starting buy !")
            game_phase.starting_buy = True
            await send_streamerbot_ws_request(ws, game_phase)
            continue

        elif match_value <= 0.8 and game_phase.starting_buy:
            capture_area, template, game_phase = \
                await pause_detection(ws, game_phase)
            continue

        elif match_value >= 0.8 and game_phase.versus_screen:
            game_phase.in_game = True
            print("Woah ! You're in game now !")
            await send_streamerbot_ws_request(ws, game_phase)
            break

        await asyncio.sleep(0.01)


async def main():
    if single_instance.lock_exists(SCRIPT_NAME):
        slot = twm.manage_window(twm.WinType.DENIED, SCRIPT_NAME)
        atexit.register(denied_sdh.free_slot, slot)
        print("\n>>> Lock file is present: exiting... <<<")
    else:
        slot = twm.manage_window(twm.WinType.ACCEPTED,
                                 SCRIPT_NAME, SECONDARY_WINDOWS)
        single_instance.create_lock_file(SCRIPT_NAME)
        atexit.register(single_instance.remove_lock, SCRIPT_NAME)
        atexit.register(sdh.free_slot_by_name, SCRIPT_NAME)
        socket_server_task = asyncio.create_task(run_socket_server())
        mute_main_loop_print_feedback.set()

        ws = None
        try:
            ws = await establish_ws_connection()
            main_task = asyncio.create_task(detect_pregame_phase(ws))
            await secondary_windows_have_spawned.wait()
            twm.manage_secondary_windows(slot, SECONDARY_WINDOWS)
            mute_main_loop_print_feedback.clear()
            await main_task
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
        finally:
            socket_server_task.cancel()
            await socket_server_task
            cv.destroyAllWindows()
            if ws:
                await ws.close()


if __name__ == "__main__":
    asyncio.run(main())
    exit_countdown()
