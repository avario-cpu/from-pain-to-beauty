from dataclasses import dataclass
from enum import Enum, auto


class WinType(Enum):
    DENIED = auto()
    ACCEPTED = auto()
    SERVER = auto()


@dataclass
class SecondaryWindow:
    name: str
    width: int
    height: int
