import os

from src.config.settings import PROJECT_DIR_PATH
from src.core.termwm import SecondaryWindow

SECONDARY_WINDOWS = [SecondaryWindow("opencv_shop_scanner", 150, 100)]
SCREEN_CAPTURE_AREA = {"left": 1853, "top": 50, "width": 30, "height": 35}

# cv template image
SHOP_TEMPLATE_IMAGE_PATH = os.path.join(
    PROJECT_DIR_PATH, "src/apps/shopwatcher/data/opencv/shop_top_right_icon.jpg"
)

# ws requests
BRB_BUYING_MILK_SHOW = os.path.join(
    PROJECT_DIR_PATH, "src/apps/shopwatcher/data/ws_requests/brb_buying_milk_show.json"
)
BRB_BUYING_MILK_HIDE = os.path.join(
    PROJECT_DIR_PATH, "src/apps/shopwatcher/data/ws_requests/brb_buying_milk_hide.json"
)
DSLR_HIDE = os.path.join(
    PROJECT_DIR_PATH, "src/apps/shopwatcher/data/ws_requests/dslr_hide.json"
)
DSLR_SHOW = os.path.join(
    PROJECT_DIR_PATH, "src/apps/shopwatcher/data/ws_requests/dslr_show.json"
)
DISPLAY_TIME_SINCE_SHOP_OPENED = os.path.join(
    PROJECT_DIR_PATH,
    "src/apps/shopwatcher/data/ws_requests/display_time_since_shop_opened.json",
)

# file with time since shop opened
TIME_SINCE_SHOP_OPENED_TXT = os.path.join(
    PROJECT_DIR_PATH, "src/apps/shopwatcher/data/time_since_shop_opened.txt"
)
