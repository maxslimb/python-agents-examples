import os
from dataclasses import dataclass
import logging
import asyncio
import livekit
from services.transcription import (Transcriber,
                                    EVENT_TYPE_MONOLOGUE_FINISHED,
                                    EVENT_TYPE_MONOLOGUE_STARTED,
                                    EVENT_TYPE_MONOLOGUE_UPDATED,
                                    EVENT_TYPE_NO_SPEECH)
from .states import (State,
                     StateType,
                     State_DoingNothing,
                     State_Listening,
                     State_GeneratingResponse,
                     State_SpeakingResponse)


from services.openai.chatgpt import (ChatGPT, Message, MessageRole)
from agents.agent import Agent

PROMPT = "You are KITT, a voice assistant in a meeting created by LiveKit. \
          Keep your responses concise while still being friendly and personable. \
          If your response is a question, please append a question mark symbol to the end of it."


class Kitt(Agent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.messages = []
        self.state: State = State_DoingNothing()
        self.chat_gpt = ChatGPT()

    def on_audio_track(
        self,
        track: livekit.Track,
        participant: livekit.Participant,
    ):
        if participant.identity != "caller":
            return

        def transcriber_cb(event: Transcriber.Event):
            self._transcriber_cb(event, participant)

        transcriber = Transcriber(audio_track=track, callback=transcriber_cb)
        transcriber.start()

    def _transcriber_cb(self, event: Transcriber.Event, participant: livekit.Participant):
        print("Processing event: ", event)
        if event.type == EVENT_TYPE_MONOLOGUE_STARTED:
            if self.state.type == StateType.DOING_NOTHING:
                self._set_state(State_Listening())
        elif event.type == EVENT_TYPE_MONOLOGUE_UPDATED:
            # Do nothing in this case for now
            pass
        elif event.type == EVENT_TYPE_MONOLOGUE_FINISHED:
            self.messages.append(Message(role=MessageRole.user, content=event.text))
        elif event.type == EVENT_TYPE_NO_SPEECH:
            # Start generating a response
            if self.state.type == StateType.LISTENING and event.time_seconds > 1.0:
                self._set_state(State_GeneratingResponse())

    def _set_state(self, state: State):
        print("Changing state to: ", state.type)
        if state.type == StateType.DOING_NOTHING:
            pass
        elif state.type == StateType.LISTENING:
            pass
        elif state.type == StateType.GENERATING_RESPONSE:
            if self.state.type != StateType.LISTENING:
                logging.warning("Unexpected state transition")
                return
            asyncio.create_task(self._state_generating_response())
        elif state.type == StateType.SPEAKING_RESPONSE:
            asyncio.create_task(self._state_speaking_response(state))

        self.state = state

    async def _state_generating_response(self):
        if len(self.messages) == 0:
            print("no messages")
            return
        response = await self.chat_gpt.GenerateText(model='gpt-3.5-turbo', prompt=PROMPT, messages=self.messages)
        print(response)
        self._set_state(State_SpeakingResponse(text=response))

    async def _state_speaking_response(self, state: State_SpeakingResponse):
        self.messages.append(Message(role=MessageRole.assistant, content=state.text))
        self._set_state(State_DoingNothing())

    async def _interrupt_response(self):
        pass

    def should_process(
        self, track: livekit.TrackPublication, participant: livekit.Participant
    ) -> bool:
        return track.kind == 1
