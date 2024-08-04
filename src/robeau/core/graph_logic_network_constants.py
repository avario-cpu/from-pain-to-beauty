import enum
from enum import auto


class QuerySource(enum.Enum):
    USER = auto()
    ROBEAU = auto()
    SYSTEM = auto()
    GREETING = auto()
    ADMIN = auto()


# Query source aliases
USER = QuerySource.USER
ROBEAU = QuerySource.ROBEAU
SYSTEM = QuerySource.SYSTEM
GREETING = QuerySource.GREETING
ADMIN = QuerySource.ADMIN


"""Below are a list of transmission nodes: They are nodes either triggered by code logic (input) or that will trigger
particular code logic (output)"""

# Inputs ------------------------------------

# General
ANY_RELEVANT_USER_INPUT = "ANY RELEVANT USER INPUT"
ANY_NON_SPECIFIC_CUTOFF = "ANY NON SPECIFIC CUTOFF"

# Expectations
EXPECTATIONS_SET = "EXPECTATIONS SET"
EXPECTATIONS_SUCCESS = "EXPECTATIONS SUCCESS"
EXPECTATIONS_FAILURE = "EXPECTATIONS FAILURE"

# Greeting
ANY_MATCHING_PROMPT = "ANY MATCHING PROMPT"
ANY_MATCHING_WHISPER = "ANY MATCHING WHISPER"
NO_MATCHING_PROMPT = "NO MATCHING PROMPT"

# Robeau mad
ROBEAU_NO_MORE_STUBBORN = "ROBEAU NO MORE STUBBORN"
ANY_MATCHING_PLEA = "ANY MATCHING PLEA"


# Outputs -----------------------------------

# General
STOP_LISTENING_FOR_WHISPERS = "STOP LISTENING FOR WHISPERS"

# Expectations
RESET_EXPECTATIONS = "RESET EXPECTATIONS"

# Robeau mad
SET_ROBEAU_UNRESPONSIVE = "SET ROBEAU UNRESPONSIVE"
SET_ROBEAU_STUBBORN = "SET ROBEAU STUBBORN"
PROLONG_STUBBORN = "PROLONG STUBBORN"


# List used to check if a reached node is an output message when processing a node chain.
transmission_output_nodes = [
    RESET_EXPECTATIONS,
    SET_ROBEAU_UNRESPONSIVE,
    SET_ROBEAU_STUBBORN,
    PROLONG_STUBBORN,
    STOP_LISTENING_FOR_WHISPERS,
]
