import os
import time

import cv2 as cv
import mss
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
        # Define a screen part to capture
        monitor = {"left": x, "top": y, "width": w, "height": h}

        # Capture the screen region and store it as a mss Class
        img = sct.grab(monitor)

        # Convert it to a numpy array: necessary to be treated with openCV
        img = np.array(img)
    return img


def scan_for_shop(template, ws=None):
    shop_is_currently_open = False

    while True:

        screenshot = window_capture()
        cv.imshow('Computer Vision', screenshot)
        cv.imwrite('opencv/last_frame.jpg', screenshot)

        snapshot = cv.imread('opencv/last_frame.jpg')
        result = cv.matchTemplate(snapshot,
                                  template,
                                  cv.TM_SQDIFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)

        # End loop if Q is pressed while having the openCV window on focus
        if cv.waitKey(1) == ord("q"):
            break

        # End loop if the file "terminate" (created by a bat file) is detected
        if os.path.isfile("temp/terminate_scan.txt"):
            # script via my StreamDeck HID.
            break

        print(max_val)

        # Detect, according to a threshold value, whether the shop is open.
        if max_val <= 0.4:

            if shop_is_currently_open:
                # If the shop was already open at the last check, do nothing
                # and keep the loop running.
                wait()
                continue
            else:
                # Else, if the shop just opened: send a request to the
                # websocket server
                shop_is_currently_open = True
                if ws:
                    client.request_hide_dslr(ws)
                print('opened shop')
                wait()

        else:  # If the shop is detected as closed...

            if shop_is_currently_open:
                # Send a request to the WS server, and set shop as closed
                shop_is_currently_open = False
                if ws:
                    client.request_show_dslr(ws)
                print('closed shop')
                wait()
            else:
                # If the shop was already closed at the last check, do nothing
                # and keep the loop running.
                wait()
                continue

    # when the loop breaks: destroy openCV windows, disconnect client
    print("loop terminated")
    cv.destroyAllWindows()
    if ws:
        client.disconnect(ws)


def run(ws_mode=""):
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
