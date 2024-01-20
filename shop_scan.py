import cv2 as cv
import time
import mss
import numpy as np
import client
import os

dota_shop_template = cv.imread('dota_pinned_items.png')  # image used for matching Dota2 shop UI


def wait():  # used to slow down the script.
    time.sleep(0.01)
    pass


def window_capture():
    x = 1520
    y = 707
    w = 400
    h = 70

    with mss.mss() as sct:
        monitor = {"left": x, "top": y, "width": w, "height": h}  # screen part to capture
        img = sct.grab(monitor)
        img = np.array(img)
    return img


def detect_shop():
    shop_is_open = False

    while "Screen capturing":

        screenshot = window_capture()
        cv.imshow('Computer Vision', screenshot)
        cv.imwrite('snapshot.jpg', screenshot)

        snapshot = cv.imread('snapshot.jpg')  # last scanned frame of my screen
        result = cv.matchTemplate(snapshot, dota_shop_template, cv.TM_SQDIFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)

        if cv.waitKey(1) == ord("q"):
            cv.destroyAllWindows()
            break

        print(max_val)

        if os.path.isfile("temp/terminate.txt"):  # this file is created by a batch file executed from an Elgato
            # StreamDeck macro: this is the only way I've found to terminate the script using this device yet.
            break

        if max_val <= 0.4:
            if shop_is_open:
                wait()
                continue
            else:  # if shop wasn't open last check ...
                shop_is_open = True
                client.toggle_dslr()  # ...send a request to the Websocket server to trigger a Streamer.bot Action
                wait()
        else:  # if there is no open shop detected with openCV...
            if shop_is_open:  # ...but the shop was open during the last check...
                shop_is_open = False
                client.toggle_dslr()  # ...send a request to the Websocket server to trigger a Streamer.bot Action
                wait()
            else:
                wait()
                continue
