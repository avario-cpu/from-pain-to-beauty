class Tabbed:
    def __init__(self):
        self._to_desktop = False
        self._to_dota_menu = False
        self._to_settings_screen = False
        self._in_game = False

    @property
    def to_desktop(self):
        return self._to_desktop

    @to_desktop.setter
    def to_desktop(self, value):
        if value:
            self._set_all_false()
        self._to_desktop = value

    @property
    def to_dota_menu(self):
        return self._to_dota_menu

    @to_dota_menu.setter
    def to_dota_menu(self, value):
        if value:
            self._set_all_false()
        self._to_dota_menu = value

    @property
    def to_settings_screen(self):
        return self._to_settings_screen

    @to_settings_screen.setter
    def to_settings_screen(self, value):
        if value:
            self._set_all_false()
        self._to_settings_screen = value

    @property
    def in_game(self):
        return self._in_game

    @in_game.setter
    def in_game(self, value):
        if value:
            self._set_all_false()
        self._in_game = value

    def _set_all_false(self):
        for attr in self.__dict__:
            if isinstance(self.__dict__[attr], bool):
                self.__dict__[attr] = False

    def current_state(self):
        if self._to_desktop:
            return "Out to desktop"
        elif self._to_dota_menu:
            return "In Dota menu"
        elif self._to_settings_screen:
            return "In settings screen"
        else:
            return "No state is True"
