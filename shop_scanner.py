import os
import time

import cv2 as cv
import mss
import numpy
import numpy as np

import client


def init():
    # Remove the previous existing file that terminated the loop.
    if os.path.exists("temp/terminate_scan.txt"):
        os.remove("temp/terminate_scan.txt")

    # Define the image to look for when template matching
    template = cv.imread('opencv/dota_shop_top_right_icon.jpg')
    return template


def wait():  # used to slow down the script.
    time.sleep(0.5)
    pass


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

        # Convert the mss object to a numpy array: needed for openCV methods.
        img = np.array(img)
    return img


def scan_for_shop(template: numpy.ndarray, ws: any = None):
    """
    Look for an indication on the screen that the dota Shop is open
    and react whenever it switches from closed to open and inversely.

    :param template: the template image used to look for a match with the
    shop UI, converted into a numpy array.
    :param ws: any "ws" parameter passed will trigger the use of the
    client to send websocket requests in reaction to the image detection.
    :return: None
    """
    shop_is_currently_open = False

    while not os.path.exists("temp/stop.flag"):
        frame = window_capture()
        cv.imshow('Computer Vision', frame)
        cv.imwrite('opencv/last_frame.jpg', frame)

        # Compare that frame with a pre-established template
        snapshot = cv.imread('opencv/last_frame.jpg')
        result = cv.matchTemplate(snapshot,
                                  template,
                                  cv.TM_SQDIFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)

        if cv.waitKey(1) == ord("q"):
            break

        print(max_val)

        # Detect, according to a threshold value, whether the shop is open.
        if max_val <= 0.4:

            if shop_is_currently_open:  # if the shop was already open...
                wait()
                continue
            else:
                shop_is_currently_open = True
                if ws:
                    client.request_hide_dslr(ws)
                print('opened shop')
                wait()

        else:  # If the shop is detected as closed...

            if shop_is_currently_open:
                shop_is_currently_open = False
                if ws:
                    client.request_show_dslr(ws)
                print('closed shop')
                wait()
            else:  # if the shop was already closed
                wait()
                continue

    # When the loop breaks: disconnect, destroy cv windows, etc.
    print("loop terminated")
    cv.destroyAllWindows()

    if ws:
        client.disconnect(ws)
    try:
        os.remove("temp/stop.flag")
    except OSError as e:
        print(e)


def run(ws_mode: str = ""):
    """Runs the main loop, either with or without using the client module to
     connect to the Streamerbot websocket"""
    template = init()
    if ws_mode == "ws":
        ws = client.init()
        try:
            scan_for_shop(template, ws)
        except KeyboardInterrupt:
            client.disconnect(ws)
            print("KeyboardInterrupt")
    else:
        try:
            scan_for_shop(template)
        except KeyboardInterrupt:
            print("KeyboardInterrupt")


def main():
    """This function is only used for testing when using this script as a main
    module """

    # decide if you want to connect to the websocket client
    ws_mode = input("run with websocket client ?: [w/any]")
    if ws_mode == "w":
        run("ws")
    else:
        run()


if __name__ == "__main__":
    main()
