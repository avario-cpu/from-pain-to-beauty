import cv2 as cv

from src.core.terminal_window_manager_v4 import SecondaryWindow

# Opencv windows parameters, for resizing and moving using terminal_window_manager_v4
SECONDARY_WINDOWS = [
    SecondaryWindow("hero_pick_scanner", 150, 80),
    SecondaryWindow("starting_buy_scanner", 150, 80),
    SecondaryWindow("dota_tab_scanner", 150, 80),
    SecondaryWindow("desktop_tab_scanner", 150, 80),
    SecondaryWindow("settings_scanner", 150, 80),
    SecondaryWindow("in_game_scanner", 150, 100),
]


# Screen areas
DOTA_TAB_AREA = {"left": 1860, "top": 10, "width": 60, "height": 40}
STARTING_BUY_AREA = {"left": 860, "top": 120, "width": 400, "height": 30}
IN_GAME_AREA = {"left": 1820, "top": 1020, "width": 80, "height": 60}
PLAY_DOTA_BUTTON_AREA = {"left": 1525, "top": 1005, "width": 340, "height": 55}
DESKTOP_TAB_AREA = {"left": 1750, "top": 1040, "width": 50, "height": 40}
SETTINGS_AREA = {"left": 170, "top": 85, "width": 40, "height": 40}
HERO_PICK_AREA = {"left": 1658, "top": 1028, "width": 62, "height": 38}
NEW_CAPTURE_AREA = {"left": 0, "top": 0, "width": 0, "height": 0}


# Path to open CV templates
DOTA_TAB_TEMPLATE = cv.imread(
    "src/apps/pregame_phase_detector/data/opencv/dota_menu_power_icon.jpg",
    cv.IMREAD_GRAYSCALE,
)
IN_GAME_TEMPLATE = cv.imread(
    "src/apps/pregame_phase_detector/data/opencv/dota_courier_deliver_items_icon.jpg",
    cv.IMREAD_GRAYSCALE,
)
STARTING_BUY_TEMPLATE = cv.imread(
    "src/apps/pregame_phase_detector/data/opencv/dota_strategy-load-out-world-guides.jpg",
    cv.IMREAD_GRAYSCALE,
)
PLAY_DOTA_BUTTON_TEMPLATE = cv.imread(
    "src/apps/pregame_phase_detector/data/opencv/dota_play_dota_button.jpg",
    cv.IMREAD_GRAYSCALE,
)
DESKTOP_TAB_TEMPLATE = cv.imread(
    "src/apps/pregame_phase_detector/data/opencv/windows_desktop_icons.jpg",
    cv.IMREAD_GRAYSCALE,
)
SETTINGS_TEMPLATE = cv.imread(
    "src/apps/pregame_phase_detector/data/opencv/dota_settings_icon.jpg",
    cv.IMREAD_GRAYSCALE,
)
HERO_PICK_TEMPLATE = cv.imread(
    "src/apps/pregame_phase_detector/data/opencv/dota_hero_select_chat_icons.jpg",
    cv.IMREAD_GRAYSCALE,
)


# Paths to JSON request files for scene changes
SCENE_CHANGE_IN_GAME = (
    "src/apps/pregame_phase_detector/data/ws_requests/scene_change_in_game.json"
)
SCENE_CHANGE_DSLR_MOVE_HERO_PICK = "src/apps/pregame_phase_detector/data/ws_requests/scene_change_dslr_move_hero_pick.json"
DSLR_MOVE_STARTING_BUY = (
    "src/apps/pregame_phase_detector/data/ws_requests/dslr_move_starting_buy.json"
)
DSLR_HIDE_VS_SCREEN = (
    "src/apps/pregame_phase_detector/data/ws_requests/dslr_hide_vs_screen.json"
)
