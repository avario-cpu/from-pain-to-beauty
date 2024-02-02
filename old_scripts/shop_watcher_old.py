import os
import time

import cv2 as cv
import mss
import numpy as np
from skimage.metrics import structural_similarity as ssim

import client
from enum import Enum, auto
import threading
import psutil

# List all the secondary windows names that will be required for the
# terminal_window_manager module in order to adjust their positions.
secondary_window = 'opencv_shop_scanner'
secondary_windows = [secondary_window]

start_event = threading.Event()
current_process = psutil.Process(os.getpid())
silence_print = True


class ConnectionType(Enum):
    """Used to run the main loop with or without websocket usage"""
    WEBSOCKET = auto()
    NONE = auto()


def wait():  # used to slow down the script.
    time.sleep(0.01)


def window_capture():
    """Capture a specific part of the screen and returns it as a numpy
    array."""
    x = 1883
    y = 50
    w = 37
    h = 35

    with mss.mss() as sct:
        monitor_area = {"left": x, "top": y, "width": w, "height": h}
        img = sct.grab(monitor_area)
        img = np.array(img)  # necessary for openCV methods.
    return img


def compare_images(image_a, image_b):
    """Compute the SSIM between two images. SSIM values range between
    -1 and 1, where "1" means perfect similarity. Works best when the images
    compared are grayscale. """
    return ssim(image_a, image_b)


def react_to_shop_just_opened(ws):
    if ws:
        client.request_hide_dslr(ws)
    print('\nopened shop')
    pass


def react_to_shop_just_closed(ws):
    if ws:
        client.request_show_dslr(ws)
    print('\nclosed shop')
    wait()
    pass


def scan_for_shop(ws=None):
    """
    Look for an indication on the screen that the Dota2 shop is open,
    and react whenever it toggles between open/closed.

    :param ws: websocket :class:`ClientConnection` instance used to send
        requests in reaction to the image detection.
    """
    shop_is_currently_open = False
    template = cv.imread(
        '../opencv/dota_shop_top_right_icon.jpg', cv.IMREAD_GRAYSCALE)

    frame_count = 0
    start_time = time.time()
    fps = 0
    cpu_usage = 0

    start_event.set()  # used to communicate to main that the loop started
    print("started loop")

    while not os.path.exists("temp/stop.flag"):
        # Set variable used for fps counting
        frame_count += 1
        current_time = time.time()
        elapsed_time = current_time - start_time

        frame = window_capture()
        gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        cv.imshow(secondary_window, gray_frame)

        match_value = compare_images(gray_frame, template)

        # Calculate FPS and cpu usage, only once every second
        if elapsed_time >= 1.0:
            fps = frame_count / elapsed_time
            frame_count = 0
            start_time = current_time
            cpu_usage = current_process.cpu_percent()

        print(f"SSIM: {round(match_value, 10)}\tFPS:{round(fps)}\t"
              f"CPU:{cpu_usage}%", end='\r')

        # Detect, according to a threshold value, whether the shop is open.
        if match_value >= 0.8:

            # If the shop is detected as open...
            if shop_is_currently_open:
                # ... And already was at the last check: do nothing
                wait()
                continue
            else:
                # ... And was closed at the last check: react
                shop_is_currently_open = True
                react_to_shop_just_opened(ws)
                wait()
        else:
            # If the shop is detected as closed...
            if shop_is_currently_open:
                # ... And was open at the last check: react
                shop_is_currently_open = False
                react_to_shop_just_closed(ws)
                wait()
            else:
                # ... And was already closed at the last check: do nothing
                wait()
                continue

        # When the loop breaks...
    print("\nloop terminated")
    cv.destroyAllWindows()
    os.remove("temp/stop.flag")
    if ws:
        client.disconnect(ws)


def start(connection_type: ConnectionType = ConnectionType.NONE):
    """Runs the main loop, either with or without using websockets"""
    ws = None
    if os.path.exists("temp/stop.flag"):
        os.remove("temp/stop.flag")
    try:
        if connection_type == ConnectionType.WEBSOCKET:
            ws = client.init()
        scan_for_shop(ws)
    except KeyboardInterrupt:
        if connection_type == ConnectionType.WEBSOCKET:
            client.disconnect(ws)
        print("KeyboardInterrupt")


def main():
    # decide if you want to connect to the websocket client
    ws_mode = input("run with websocket client ?: [w/any]")
    if ws_mode == "w":
        start(ConnectionType.WEBSOCKET)
    else:
        start()


if __name__ == "__main__":
    main()
