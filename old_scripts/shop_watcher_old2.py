import os
import time
import cv2 as cv
import mss
import numpy as np
from skimage.metrics import structural_similarity as ssim
from old_scripts import client
from enum import Enum, auto
import threading
import psutil
import logging

# Configuration
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
SCREEN_CAPTURE_AREA = {"left": 1883, "top": 50, "width": 37, "height": 35}
TEMPLATE_IMAGE_PATH = '../opencv/dota_shop_top_right_icon.jpg'
STOP_FLAG_PATH = "temp/stop.flag"
SECONDARY_WINDOW_NAMES = ['opencv_shop_scanner']
start_event = threading.Event()


class ConnectionType(Enum):
    WEBSOCKET = auto()
    NONE = auto()


def capture_window(area):
    with mss.mss() as sct:
        img = sct.grab(area)
    return np.array(img)


def compare_images(image_a, image_b):
    return ssim(image_a, image_b)


def setup_websocket_connection(connection_type):
    if connection_type == ConnectionType.WEBSOCKET:
        return client.init()
    return None


def cleanup_websocket_connection(ws, connection_type):
    if connection_type == ConnectionType.WEBSOCKET and ws:
        client.disconnect(ws)


def scan_for_shop(ws=None):
    shop_is_currently_open = False
    template = cv.imread(TEMPLATE_IMAGE_PATH, cv.IMREAD_GRAYSCALE)
    frame_count, start_time = 0, time.time()
    fps, cpu_usage = 0, 0
    current_process = psutil.Process(os.getpid())
    start_event.set()

    while not os.path.exists(STOP_FLAG_PATH):
        frame_count += 1
        frame = capture_window(SCREEN_CAPTURE_AREA)
        gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        cv.imshow(SECONDARY_WINDOW_NAMES[0], gray_frame)

        if cv.waitKey(1) == ord("q"):
            break

        match_value = compare_images(gray_frame, template)
        elapsed_time = time.time() - start_time

        if elapsed_time >= 1.0:
            fps = frame_count / elapsed_time
            cpu_usage = current_process.cpu_percent()
            frame_count, start_time = 0, time.time()

        print(f"SSIM:{match_value:.12f} FPS:{round(fps)} "
              f"CPU:{cpu_usage}%", end='\r')

        shop_is_currently_open = detect_shop_state(match_value,
                                                   shop_is_currently_open, ws)

    logging.info("Loop terminated")
    cv.destroyAllWindows()
    if os.path.exists(STOP_FLAG_PATH):
        os.remove(STOP_FLAG_PATH)


def detect_shop_state(match_value, shop_is_currently_open, ws):
    threshold = 0.8
    if match_value >= threshold:
        if not shop_is_currently_open:
            print('\nShop just opened')
            if ws:
                client.request_hide_dslr(ws)
            shop_is_currently_open = True
    else:
        if shop_is_currently_open:
            print('\nShop just closed')
            if ws:
                client.request_show_dslr(ws)
            shop_is_currently_open = False
    return shop_is_currently_open


def start(connection_type=ConnectionType.NONE):
    if os.path.exists(STOP_FLAG_PATH):
        os.remove(STOP_FLAG_PATH)
    ws = setup_websocket_connection(connection_type)
    try:
        scan_for_shop(ws)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt caught. Exiting.")
    finally:
        cleanup_websocket_connection(ws, connection_type)


def main():
    ws_mode = input("Run with websocket client? (w/any key for NO): ")
    connection_type = ConnectionType.WEBSOCKET if ws_mode.lower() == 'w' \
        else ConnectionType.NONE
    start(connection_type)


if __name__ == "__main__":
    main()
