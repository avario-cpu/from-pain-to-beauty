import cv2 as cv
import numpy as np
import time
import mss
import client
import os

dota_shop_template = cv.imread('dota_shop_top_right.jpg')  # image used for template matching the Dota2 shop UI

if os.path.exists("temp/terminate_scan.txt"):  # remove the previous existing file that terminated the loop.
    os.remove("temp/terminate_scan.txt")


def wait():  # used to slow down the script.
    time.sleep(0.5)
    pass


def window_capture():
    x = 1883
    y = 50
    w = 37
    h = 35

    with mss.mss() as sct:
        monitor = {"left": x, "top": y, "width": w, "height": h}  # screen part to capture
        img = sct.grab(monitor)
        img = np.array(img)
    return img


def scan_for_shop():
    shop_is_open = False

    while True:

        screenshot = window_capture()
        cv.imshow('Computer Vision', screenshot)
        cv.imwrite('snapshot.jpg', screenshot)

        snapshot = cv.imread('snapshot.jpg')  # most recent scanned frame of my screen
        result = cv.matchTemplate(snapshot, dota_shop_template, cv.TM_SQDIFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)

        if cv.waitKey(1) == ord("q"):  # if Q is pressed while having openCV window on focus
            break

        if os.path.isfile("temp/terminate_scan.txt"):  # this loop is manually stopped by creating a file with a batch
            # script via my StreamDeck HID.
            break

        print(max_val)

        if max_val <= 0.4:
            if shop_is_open:
                wait()
                continue
            else:  # if the shop just opened ...
                shop_is_open = True
                client.request_hide_dslr()  # ...send a request to the Websocket server to trigger a Streamer.bot Action
                wait()
        else:
            if shop_is_open:  # if the shop just closed
                shop_is_open = False
                client.request_show_dslr()  # ...send a request to the Websocket server to trigger a Streamer.bot Action
                wait()
            else:
                wait()
                continue

    # when the loop breaks: destroy openCV windows, disconnect client, and remove the single instance lock.
    cv.destroyAllWindows()

