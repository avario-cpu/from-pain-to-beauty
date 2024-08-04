import asyncio
import time

from src.apps.pregame_phase_detector.core.constants import (
    DSLR_HIDE_VS_SCREEN,
    DSLR_MOVE_FOR_HERO_PICK,
    DSLR_MOVE_STARTING_BUY,
    SCENE_CHANGE_FOR_PREGAME,
    SCENE_CHANGE_IN_GAME,
)
from src.apps.pregame_phase_detector.core.image_processor import ImageProcessor
from src.apps.pregame_phase_detector.core.pick_phase import PickPhase
from src.apps.pregame_phase_detector.core.shared_events import mute_ssim_prints
from src.apps.pregame_phase_detector.core.tabbed import Tabbed
from src.connection.websocket_client import WebSocketClient


class GameStateManager:
    def __init__(self, image_processor: ImageProcessor, ws: WebSocketClient):
        self.image_processor = image_processor
        self.ws = ws
        self.tabbed = Tabbed()
        self.game_phase = PickPhase()

    async def set_state_finding_game(self):
        self.game_phase.finding_game = True  # initial game phase
        print(
            "\n\n\n\n\n\n\nWaiting to find a game..."
        )  # to avoid forefront blocking secondary windows

    async def set_state_game_found(self):
        self.tabbed.in_game = True
        self.game_phase.hero_pick = True
        print("\nFound a game")
        await self.ws.send_json_requests(SCENE_CHANGE_FOR_PREGAME)

    async def set_back_state_hero_pick(self):
        self.tabbed.in_game = True
        self.game_phase.hero_pick = True
        print("\nBack to hero select")
        await self.ws.send_json_requests(DSLR_MOVE_FOR_HERO_PICK)

    async def set_state_starting_buy(self):
        self.tabbed.in_game = True
        self.game_phase.starting_buy = True
        print("\nStarting buy")
        await self.ws.send_json_requests(DSLR_MOVE_STARTING_BUY)

    async def set_state_vs_screen(self):
        self.tabbed.in_game = True
        self.game_phase.versus_screen = True
        await self.ws.send_json_requests(DSLR_HIDE_VS_SCREEN)
        print("\nWe are in vs screen")

    async def set_state_in_game(self):
        self.tabbed.in_game = True
        self.game_phase.in_game = True
        await self.ws.send_json_requests(SCENE_CHANGE_IN_GAME)
        print("\nWe are in now game")

    async def set_state_dota_menu(self):
        self.tabbed.to_dota_menu = True
        self.game_phase.unknown = True
        await self.ws.send_json_requests(DSLR_HIDE_VS_SCREEN)
        print("\nWe are in Dota Menus")

    async def set_state_desktop(self):
        self.tabbed.to_desktop = True
        self.game_phase.unknown = True
        print("\nWe are on desktop")

    async def set_state_settings_screen(self):
        self.tabbed.to_settings_screen = True
        self.game_phase.unknown = True
        await self.ws.send_json_requests(DSLR_HIDE_VS_SCREEN)
        print("\nWe are in settings")

    async def confirm_transition_to_vs_screen(self, target_value: float):
        start_time = time.time()
        duration = 0.5
        print("\nNo matches detected")
        mute_ssim_prints.set()

        while time.time() - start_time < duration:
            print(
                f"Checking for vs screen... ({time.time() - start_time:.4f}s elapsed.)",
                end="\r",
            )
            ssim_matches = await self.image_processor.scan_screen_for_matches()

            if max(ssim_matches.values()) >= target_value:
                print("\nNot in vs screen")
                break
            elif time.time() - start_time >= duration:
                # The condition was true for the entire 0.5 seconds
                await self.set_state_vs_screen()
                break
        mute_ssim_prints.clear()

    async def wait_for_settings_screen_exiting_fade_out(self):
        self.tabbed.to_settings_screen = False
        await asyncio.sleep(0.25)

    async def wait_for_starting_buy_screen_transition_out(self):
        self.game_phase.starting_buy = False
        await asyncio.sleep(0.6)
