import os
import time

import cv2 as cv
import mss
import numpy as np
from skimage.metrics import structural_similarity as ssim

import client
from enum import Enum, auto

secondary_window = 'opencv_shop_scanner'
secondary_windows = [secondary_window]  # used in terminal_window_manager


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
    print('opened shop')
    pass


def react_to_shop_just_closed(ws):
    if ws:
        client.request_show_dslr(ws)
    print('closed shop')
    wait()
    pass


def scan_for_shop(ws=None):
    """
    Look for an indication on the screen that the dota Shop is open,
    and react whenever it toggles between open/closed.

    :param ws: websocket class object used to send requests in reaction to the
    image detection.
    :return: None.
    """
    shop_is_currently_open = False
    template = cv.imread(
        'opencv/dota_shop_top_right_icon.jpg', cv.IMREAD_GRAYSCALE)

    while not os.path.exists("temp/stop.flag"):
        frame = window_capture()
        gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        cv.imshow(secondary_window, gray_frame)

        match_value = compare_images(gray_frame, template)

        if cv.waitKey(1) == ord("q"):
            break

        print(f"SSIM: {match_value}", end='\r')

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
            else:
                # ... And was already closed at the last check: do nothing
                wait()
                continue

    # When the loop breaks...
    print("loop terminated")
    cv.destroyAllWindows()
    os.remove("temp/stop.flag")
    if ws:
        client.disconnect(ws)


def start(connection_type: ConnectionType = ConnectionType.NONE):
    """Runs the main loop, either with or without using websockets"""
    ws = None
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
