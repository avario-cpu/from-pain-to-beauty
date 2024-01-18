import cv2 as cv
import time
import mss
import numpy as np

import os

dota_shop = cv.imread('dota_pinned_items.png')


def slowdown_script():
    # print(f'FPS {(1 / (time.time() - last_time))}')
    time.sleep(1)


def window_capture():
    # Define your Monitor
    x = 1520
    y = 707
    w = 400
    h = 70

    with mss.mss() as sct:
        # Part of the screen to capture
        monitor = {"left": x, "top": y, "width": w, "height": h}
        img = sct.grab(monitor)
        img = np.array(img)
    return img


def detect_shop():
    shop_is_open = False

    if os.listdir('watched_folder_shop_shown')[0] == 'renamed.txt':
        shop_shown_folder_is_renamed = True
    else:
        shop_shown_folder_is_renamed = False

    if os.listdir('watched_folder_shop_hidden')[0] == 'renamed.txt':
        shop_hidden_folder_is_renamed = True
    else:
        shop_hidden_folder_is_renamed = False

    print('listdir:', os.listdir('watched_folder_shop_shown')[0])

    print('shown:', shop_shown_folder_is_renamed)
    print('hidden:', shop_hidden_folder_is_renamed)

    while "Screen capturing":
        # Define Time
        last_time = time.time()

        # Get the img
        screenshot = window_capture()

        # Display the picture
        cv.imshow('Computer Vision', screenshot)

        # See if the template matches
        cv.imwrite('snapshot.jpg', screenshot)
        snapshot = cv.imread('snapshot.jpg')
        result = cv.matchTemplate(snapshot, dota_shop, cv.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)

        # Press "q" to quit
        if cv.waitKey(1) == ord("q"):
            cv.destroyAllWindows()
            break

        if max_val >= 0.3:  # if successful match with openCV
            if shop_is_open:
                print('shop was already open, continue.')
                slowdown_script()
                continue
            else:
                shop_is_open = True
                print('\n\nshop just opened, renaming file\n\n')
                if shop_shown_folder_is_renamed:
                    os.rename('watched_folder_shop_shown/renamed.txt', 'watched_folder_shop_shown/rename.txt')
                    shop_shown_folder_is_renamed = False
                    slowdown_script()
                else:
                    os.rename('watched_folder_shop_shown/rename.txt', 'watched_folder_shop_shown/renamed.txt')
                    shop_shown_folder_is_renamed = True
                    slowdown_script()

        else:  # if no successful match with openCV = shop is closed
            if shop_is_open:  # if the shop was open during the last check
                shop_is_open = False
                print('\n\nshop just closed, renaming file\n\n')
                if shop_hidden_folder_is_renamed:
                    os.rename('watched_folder_shop_hidden/renamed.txt', 'watched_folder_shop_hidden/rename.txt')
                    shop_hidden_folder_is_renamed = False
                    slowdown_script()
                else:
                    os.rename('watched_folder_shop_hidden/rename.txt', 'watched_folder_shop_hidden/renamed.txt')
                    shop_hidden_folder_is_renamed = True
                    slowdown_script()
            else:
                print('Shop was already closed, continue')
                slowdown_script()
                continue


detect_shop()
