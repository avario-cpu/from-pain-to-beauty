import os
import time

import cv2 as cv
import mss
import numpy
import numpy as np

import client
from enum import Enum, auto

secondary_window = 'opencv_shop_scanner'
secondary_windows = [secondary_window]  # used in terminal_window_manager
# module to manage secondary window placement. E.g. the small openCV window
# that spawns with this script.


class ConnectionType(Enum):
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


def scan_for_shop(template: numpy.ndarray, ws=None):
    """
    Look for an indication on the screen that the dota Shop is open,
    and react whenever it toggles between open/closed.

    :param template: the template image used to look for a match with the
    shop UI, converted into a numpy array.
    :param ws: any "ws" parameter passed will trigger the use of the
    client to send websocket requests in reaction to the image detection. If
    None, the script will run without client communication.
    :return: None
    """
    shop_is_currently_open = False

    while not os.path.exists("temp/stop.flag"):
        frame = window_capture()
        cv.imshow(secondary_window, frame)
        cv.imwrite('opencv/last_frame.jpg', frame)

        # Compare that frame with a pre-established template
        snapshot = cv.imread('opencv/last_frame.jpg')
        result = cv.matchTemplate(snapshot,
                                  template,
                                  cv.TM_SQDIFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)

        if cv.waitKey(1) == ord("q"):
            break

        # print(max_val)

        # Detect, according to a threshold value, whether the shop is open.
        if max_val <= 0.4:

            # If the shop is detected as open...
            if shop_is_currently_open:
                # ... But already was at the last check, do nothing
                wait()
                continue
            else:
                # ... But was closed at the last check, react
                shop_is_currently_open = True
                react_to_shop_just_closed(ws)
                wait()
        else:
            # If the shop is detected as closed...
            if shop_is_currently_open:
                # ... But was open at the last check, react
                shop_is_currently_open = False
                react_to_shop_just_closed(ws)
            else:
                # ... But was already closed at the last check, do nothing
                wait()
                continue

    # When the loop breaks...
    print("loop terminated")
    cv.destroyAllWindows()
    os.remove("temp/stop.flag")
    if ws:
        client.disconnect(ws)


def start(connection_type: ConnectionType = ConnectionType.NONE):
    """Runs the main loop, either with or without using the client module to
     connect to the Streamerbot websocket"""

    cv_template = cv.imread('opencv/dota_shop_top_right_icon.jpg')
    ws = None
    try:
        if connection_type == ConnectionType.WEBSOCKET:
            ws = client.init()
        scan_for_shop(cv_template, ws)
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
