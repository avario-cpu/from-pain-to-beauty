import cv2 as cv
import numpy as np
import time
import mss
import client
import os
import keyboard

dota_shop_template = cv.imread('dota_shop_top_right.jpg')  # image used for template matching the Dota2 shop UI
break_loop = False


def wait():  # used to slow down the script.
    time.sleep(0.01)
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

        if break_loop:
            break

        if max_val <= 0.4:
            if shop_is_open:
                wait()
                continue
            else:  # if the shop just opened ...
                shop_is_open = True
                client.hide_dslr()  # ...send a request to the Websocket server to trigger a Streamer.bot Action
                wait()
        else:
            if shop_is_open:  # if the shop just closed
                shop_is_open = False
                client.show_dslr()  # ...send a request to the Websocket server to trigger a Streamer.bot Action
                wait()
            else:
                wait()
                continue


# if __name__ == "__main__":
#     detect_shop()
