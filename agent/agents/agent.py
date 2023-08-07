from enum import Enum


class AgentType(Enum):
    Audio = 1 << 0
    Video = 1 << 1


class Agent:
    def get_type(self) -> AgentType:
        raise NotImplementedError

    def required_processors(self) -> [str]:
        raise NotImplementedError

    def track_filter(self, track, participant) -> bool:
        return True
