class PickPhase:

    def __init__(self):
        self._finding_game = False
        self._hero_pick = False
        self._starting_buy = False
        self._versus_screen = False
        self._in_game = False
        self._unknown = False

    @property
    def finding_game(self):
        return self._finding_game

    @finding_game.setter
    def finding_game(self, value):
        if value:
            self._set_all_false()
        self._finding_game = value

    @property
    def hero_pick(self):
        return self._hero_pick

    @hero_pick.setter
    def hero_pick(self, value):
        if value:
            self._set_all_false()
        self._hero_pick = value

    @property
    def starting_buy(self):
        return self._starting_buy

    @starting_buy.setter
    def starting_buy(self, value):
        if value:
            self._set_all_false()
        self._starting_buy = value

    @property
    def versus_screen(self):
        return self._versus_screen

    @versus_screen.setter
    def versus_screen(self, value):
        if value:
            self._set_all_false()
        self._versus_screen = value

    @property
    def in_game(self):
        return self._in_game

    @in_game.setter
    def in_game(self, value):
        if value:
            self._set_all_false()
        self._in_game = value

    @property
    def unknown(self):
        return self._unknown

    @unknown.setter
    def unknown(self, value):
        if value:
            self._set_all_false()
        self._unknown = value

    def _set_all_false(self):
        for attr in self.__dict__:
            if isinstance(self.__dict__[attr], bool):
                self.__dict__[attr] = False
