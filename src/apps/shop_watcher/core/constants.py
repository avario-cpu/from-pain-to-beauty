from src.core.terminal_window_manager_v4 import SecondaryWindow

SECONDARY_WINDOWS = [SecondaryWindow("opencv_shop_scanner", 150, 100)]
SCREEN_CAPTURE_AREA = {"left": 1853, "top": 50, "width": 30, "height": 35}

# cv template image
SHOP_TEMPLATE_IMAGE_PATH = "src/apps/shop_watcher/data/opencv/shop_top_right_icon.jpg"

# ws requests
BRB_BUYING_MILK_SHOW = (
    "src/apps/shop_watcher/data/ws_requests/brb_buying_milk_show.json"
)
BRB_BUYING_MILK_HIDE = (
    "src/apps/shop_watcher/data/ws_requests/brb_buying_milk_hide.json"
)
DSLR_HIDE = "src/apps/shop_watcher/data/ws_requests/dslr_hide.json"
DSLR_SHOW = "src/apps/shop_watcher/data/ws_requests/dslr_show.json"
DISPLAY_TIME_SINCE_SHOP_OPENED = (
    "src/apps/shop_watcher/data/ws_requests/display_time_since_shop_opened.json"
)

# file with time since shop opened
TIME_SINCE_SHOP_OPENED_TXT = "src/apps/shop_watcher/data/time_since_shop_opened.txt"
