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
        self._in_game = False
        self._out_game = False

    @property
    def in_game(self):
        return self._in_game

    @in_game.setter
    def in_game(self, value):
        if value:
            self._set_all_false()
        self._in_game = value

    @property
    def out_game(self):
        return self._out_game

    @out_game.setter
    def out_game(self, value):
        if value:
            self._set_all_false()
        self._out_game = value

    def _set_all_false(self):
        self._in_game = False
        self._out_game = False


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


DOTA_POWER_ICON_AREA = {"left": 1860, "top": 10, "width": 60, "height": 40}
PICK_TIMER_DOTS_AREA = {"left": 937, "top": 24, "width": 14, "height": 40}
PICK_PHASE_MESSAGE_AREA = {"left": 880, "top": 70, "width": 160, "height": 24}
STARTING_BUY_AREA = {"left": 860, "top": 120, "width": 400, "height": 30}
IN_GAME_AREA = {"left": 1820, "top": 1020, "width": 80, "height": 60}
PLAY_DOTA_BUTTON_AREA = {"left": 1525, "top": 1005, "width": 340, "height": 55}
DESKTOP_ICONS_AREA = {"left": 1750, "top": 1040, "width": 50, "height": 40}

DOTA_POWER_ICON_TEMPLATE = cv2.imread("opencv/dota_power_icon.jpg",
                                      cv.IMREAD_GRAYSCALE)
ALL_PICK_TEMPLATE = cv2.imread("opencv/all_pick.jpg", cv.IMREAD_GRAYSCALE)
STRATEGY_TIME_TEMPLATE = cv2.imread("opencv/strategy_time.jpg",
                                    cv.IMREAD_GRAYSCALE)
IN_GAME_TEMPLATE = cv2.imread("opencv/deliver_items_icon.jpg",
                              cv.IMREAD_GRAYSCALE)
STARTING_BUY_TEMPLATE = cv2.imread("opencv/strategy-load-out-world-guides.jpg",
                                   cv.IMREAD_GRAYSCALE)
PLAY_DOTA_BUTTON_TEMPLATE = cv2.imread("opencv/play_dota.jpg",
                                       cv.IMREAD_GRAYSCALE)
DESKTOP_ICONS_TEMPLATE = cv2.imread("opencv/desktop_icons.jpg",
                                    cv.IMREAD_GRAYSCALE)

SECONDARY_WINDOWS = [my.SecondaryWindow("pick_timer_scanner", 200, 80),
                     my.SecondaryWindow("starting_buy_scanner", 400, 80),
                     my.SecondaryWindow("interruption_scanner", 200, 80)]
SCRIPT_NAME = constants.SCRIPT_NAME_SUFFIX + os.path.splitext(
    os.path.basename(__file__))[0] if __name__ == "__main__" else __name__
# suffix added to avoid window naming conflicts with cli manager
STREAMERBOT_WS_URL = "ws://127.0.0.1:50001/"

initial_secondary_windows_spawned = asyncio.Event()
secondary_windows_readjusted = asyncio.Event()
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
logger.info("\n\n\n\n<< New Log Entry >>")


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


async def compare_multiple_images_to_one(
        image_a, image_b1, image_b2):
    score1 = await compare_images(image_a, image_b1)
    score2 = await compare_images(image_a, image_b2)
    return max(score1, score2)


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


async def send_streamerbot_ws_request(ws: websockets.WebSocketClientProtocol,
                                      game_phase: PreGamePhases):
    if game_phase.in_game:
        await send_json_requests(
            ws,
            "streamerbot_ws_requests/switch_to_meta_scene.json")
    elif game_phase.versus_screen:
        await send_json_requests(
            ws,
            "streamerbot_ws_requests/dslr_hide_for_VS_screen.json")
    elif game_phase.starting_buy:
        await send_json_requests(
            ws,
            "streamerbot_ws_requests/dslr_move_for_starting_buy.json")
    elif game_phase.hero_pick:
        await send_json_requests(
            ws,
            "streamerbot_ws_requests/scene_change_and_dslr_move_for_pick.json")
    elif game_phase.finding_game:
        await send_json_requests(
            ws,
            "streamerbot_ws_requests/switch_to_meta_scene.json")


async def capture_new_area(capture_area, filename):
    frame = await capture_window(capture_area)
    gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    cv.imshow("new_area_capture", gray_frame)
    initial_secondary_windows_spawned.set()
    cv.imwrite(filename, gray_frame)


async def readjust_secondary_windows():
    sdh_slot = sdh.get_slot_by_main_name(SCRIPT_NAME)
    logger.debug(f"Obtained slot from db is {sdh_slot}. Resizing "
                 f"secondary windows ")
    twm.manage_secondary_windows(sdh_slot, SECONDARY_WINDOWS)


async def match_interrupt_template(area, template):
    frame = await capture_window(area)
    gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    cv.imshow(SECONDARY_WINDOWS[2].name, gray_frame)
    match_value = await compare_images(gray_frame, template)
    return match_value


async def capture_and_process_images(capture_area_a,
                                     template_a1: cv2.typing.MatLike,
                                     template_a2: cv2.typing.MatLike = None,
                                     capture_area_b=None,
                                     template_b: cv2.typing.MatLike = None):
    # Capture and process first area
    frame_1 = await capture_window(capture_area_a)
    gray_frame_1 = cv.cvtColor(frame_1, cv.COLOR_BGR2GRAY)

    if template_a2 is not None:
        match_value_1 = await compare_multiple_images_to_one(
            gray_frame_1, template_a1, template_a2)
    else:
        match_value_1 = await compare_images(gray_frame_1, template_a1)

    cv.imshow(SECONDARY_WINDOWS[0].name, gray_frame_1)

    match_value_2 = 0.0

    if capture_area_b is not None:
        frame_2 = await capture_window(capture_area_b)
        gray_frame_2 = cv.cvtColor(frame_2, cv.COLOR_BGR2GRAY)
        cv.imshow(SECONDARY_WINDOWS[1].name, gray_frame_2)

        if template_b is not None:
            match_value_2 = await compare_images(gray_frame_2, template_b)

    initial_secondary_windows_spawned.set()

    return match_value_1, match_value_2


async def detect_pregame_phase(ws: websockets.WebSocketClientProtocol):
    game_phase = PreGamePhases()
    tabbed = Tabbed()
    game_phase.finding_game = True
    check_for_tabout = False
    counter = 0

    capture_area_a = PICK_PHASE_MESSAGE_AREA
    template_a1 = ALL_PICK_TEMPLATE
    template_a2 = STRATEGY_TIME_TEMPLATE

    capture_area_b = STARTING_BUY_AREA
    template_b = STARTING_BUY_TEMPLATE

    target_value_1 = 0.7  # for Pick timer message
    target_value_2 = 0.7  # for Starting buy / Tab out

    while not stop_main_loop.is_set():
        counter += 1
        match_value_1, match_value_2 = await capture_and_process_images(
            capture_area_a, template_a1, template_a2,
            capture_area_b, template_b)

        # await capture_new_area(PICK_PHASE_MESSAGE_AREA,
        #                        "opencv/strategy_time.jpg")
        # match_value_1, match_value_2 = 0, 0
        if cv.waitKey(1) == ord("q"):
            break

        if not mute_main_loop_print_feedback.is_set():
            print(f"SSIMs:{match_value_2:.4f} / {match_value_1:.4f}", end="\r")

        if check_for_tabout:
            if tabbed.out_game:
                await asyncio.sleep(0.3)
            if match_value_2 >= target_value_2:
                tabbed.out_game = True
                print(f"Detected Tab out... {counter}")
                continue
            elif (capture_area_b is not DESKTOP_ICONS_AREA
                  and template_b is not DESKTOP_ICONS_TEMPLATE):
                # Check for Desktop tabout
                capture_area_b = DESKTOP_ICONS_AREA
                template_b = DESKTOP_ICONS_TEMPLATE
                continue
            elif match_value_1 >= target_value_1:
                capture_area_b = STARTING_BUY_AREA
                template_b = STARTING_BUY_TEMPLATE
                check_for_tabout = False
                tabbed.in_game = True
                continue
            else:
                # No tabout matches and no all pick/strategy UI
                # if this last for more than 1sec, we are in vs screen,
                # until then we need to re-check if we are not
                # transitioning to a "starting buy" state
                start_time = time.time()
                duration = 0.7
                while time.time() - start_time < duration:
                    elapsed_time = time.time() - start_time
                    percentage = (elapsed_time / duration) * 100
                    print(f"Checking for Vs screen... {percentage:.2f}%",
                          end='\r')
                match_value_1, match_value_2 = await (
                    capture_and_process_images(
                        STARTING_BUY_AREA, STARTING_BUY_TEMPLATE,
                        capture_area_b=PICK_PHASE_MESSAGE_AREA,
                        template_b=STRATEGY_TIME_TEMPLATE
                    ))
                if match_value_1 >= 0.7 or match_value_2 >= 0.7:
                    print("Not in vs screen... resumed pick phase")
                    capture_area_b = STARTING_BUY_AREA
                    template_b = STARTING_BUY_TEMPLATE
                    check_for_tabout = False
                    tabbed.in_game = True
                else:
                    print("\n We should be in VS screen...")
                    game_phase.versus_screen = True
                    check_for_tabout = False
                    tabbed.in_game = True
                    cv.destroyWindow(SECONDARY_WINDOWS[1].name)
                    capture_area_a = IN_GAME_AREA
                    template_a1 = IN_GAME_TEMPLATE
                    template_a2 = None
                    capture_area_b = None
                    template_b = None
                    await send_streamerbot_ws_request(ws, game_phase)
                continue

        elif match_value_1 >= target_value_1 and game_phase.finding_game:
            # Initial all pick phase detection
            print("Found game: arrived on hero pick screen")
            game_phase.hero_pick = True
            tabbed.in_game = True
            await send_streamerbot_ws_request(ws, game_phase)
            continue

        elif (match_value_1 >= target_value_1
              and match_value_2 >= target_value_2
              and game_phase.hero_pick):
            # We detect the starting buy screen
            print("Now, this is the starting buy !")
            game_phase.starting_buy = True
            tabbed.in_game = True
            await send_streamerbot_ws_request(ws, game_phase)
            continue

        elif (match_value_1 >= target_value_1
              and match_value_2 < target_value_2
              and game_phase.starting_buy):
            # We are on the pick screen, but starting buy UI does not show.
            print("Back to hero select screen !")
            game_phase.hero_pick = True
            tabbed.in_game = True
            await send_streamerbot_ws_request(ws, game_phase)

        elif (match_value_1 < target_value_1
              and (game_phase.hero_pick or game_phase.starting_buy)):
            # We've lost track of the "all pick" screen
            check_for_tabout = True
            # Check for Dota Tab out
            capture_area_b = DOTA_POWER_ICON_AREA
            template_b = DOTA_POWER_ICON_TEMPLATE
            continue

        elif game_phase.versus_screen and match_value_1 >= 0.8:
            print("We are now in Game !")
            game_phase.in_game = True
            tabbed.in_game = True
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
        atexit.register(sdh.free_slot_named, SCRIPT_NAME)
        socket_server_task = asyncio.create_task(run_socket_server())
        mute_main_loop_print_feedback.set()

        ws = None
        try:
            ws = await establish_ws_connection()
            main_task = asyncio.create_task(detect_pregame_phase(ws))
            await initial_secondary_windows_spawned.wait()
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
