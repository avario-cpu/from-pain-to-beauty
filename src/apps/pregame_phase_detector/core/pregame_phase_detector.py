import asyncio

from src.apps.pregame_phase_detector.core.game_state_manager import GameStateManager
from src.apps.pregame_phase_detector.core.image_processor import ImageProcessor
from src.apps.pregame_phase_detector.core.socket_handler import PreGamePhaseHandler
from src.connection.websocket_client import WebSocketClient


class PreGamePhaseDetector:
    def __init__(self, socket_handler: PreGamePhaseHandler, ws_client: WebSocketClient):
        self.image_processor = ImageProcessor()
        self.state_manager = GameStateManager(self.image_processor, ws_client)
        self.socket_handler = socket_handler

    async def detect_pregame_phase(self):
        await self.state_manager.set_state_finding_game()
        target = 0.7  # target value for ssim
        while not self.socket_handler.stop_event.is_set():
            ssim_match = await self.image_processor.scan_screen_for_matches()
            await self.handle_finding_game(ssim_match, target)
            if self.state_manager.game_phase.finding_game:
                continue
            await self.wait_for_transitions(ssim_match, target)
            await self.handle_tabbed_states(ssim_match, target)
            await self.handle_pregame_phases(ssim_match, target)
            await asyncio.sleep(0.01)

    async def handle_finding_game(self, ssim_match: dict[str, float], target: float):
        if (
            ssim_match["hero_pick"] >= target
            and self.state_manager.game_phase.finding_game
        ):
            await self.state_manager.set_state_game_found()

    async def wait_for_transitions(self, ssim_match: dict[str, float], target: float):
        if (
            self.state_manager.tabbed.to_settings_screen
            and ssim_match["settings"] < target
            and ssim_match["desktop_tab"] < target
        ):
            await self.state_manager.wait_for_settings_screen_exiting_fade_out()

        elif (
            self.state_manager.game_phase.starting_buy
            and ssim_match["starting_buy"] < target
            and ssim_match["dota_tab"] < target
            and ssim_match["desktop_tab"] < target
            and ssim_match["hero_pick"] >= target
        ):
            await self.state_manager.wait_for_starting_buy_screen_transition_out()

    async def handle_tabbed_states(self, ssim_match: dict[str, float], target: float):
        if (
            ssim_match["dota_tab"] >= target
            and not self.state_manager.tabbed.to_dota_menu
        ):
            await self.state_manager.set_state_dota_menu()

        elif (
            ssim_match["desktop_tab"] >= target
            and not self.state_manager.tabbed.to_desktop
        ):
            await self.state_manager.set_state_desktop()

        elif (
            ssim_match["settings"] >= target
            and not self.state_manager.tabbed.to_settings_screen
        ):
            await self.state_manager.set_state_settings_screen()

    async def handle_pregame_phases(self, ssim_match: dict[str, float], target: float):
        if (
            ssim_match["starting_buy"] >= target
            and not self.state_manager.game_phase.starting_buy
        ):
            await self.state_manager.set_state_starting_buy()

        elif (
            ssim_match["hero_pick"] >= target > ssim_match["starting_buy"]
            and ssim_match["settings"] < target
            and ssim_match["desktop_tab"] < target
            and not self.state_manager.game_phase.hero_pick
        ):
            await self.state_manager.set_back_state_hero_pick()

        elif (
            ssim_match["in_game"] >= target
            and not self.state_manager.game_phase.in_game
        ):
            await self.state_manager.set_state_in_game()

        elif (
            max(ssim_match.values())
            < target  # nothing matching means vs screen (normally)
            and not self.state_manager.game_phase.versus_screen
        ):
            await self.state_manager.confirm_transition_to_vs_screen(target)
