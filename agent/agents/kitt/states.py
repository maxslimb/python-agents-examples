from enum import Enum
from dataclasses import dataclass

StateType = Enum('State', ['DOING_NOTHING', 'LISTENING', 'GENERATING_RESPONSE', 'SPEAKING_RESPONSE'])

class State:
    type: StateType

@dataclass
class State_DoingNothing(State):
    type = StateType.DOING_NOTHING

@dataclass
class State_Listening(State):
    type = StateType.LISTENING

@dataclass
class State_GeneratingResponse(State):
    type = StateType.GENERATING_RESPONSE
