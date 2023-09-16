import logging
import asyncio
import livekit
import services.transcription as transcription
from . import states

from services.openai.chatgpt import (ChatGPT, Message, MessageRole)
from agents.agent import Agent

PROMPT = "You are KITT, a voice assistant in a meeting created by LiveKit. \
          Keep your responses concise while still being friendly and personable. \
          If your response is a question, please append a question mark symbol to the end of it."


class Kitt(Agent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state: states.State = states.State_DoingNothing()
        self.chat_gpt = ChatGPT(prompt=PROMPT, message_capacity=20)

    def on_audio_track(
        self,
        track: livekit.Track,
        participant: livekit.Participant,
    ):
        if participant.identity != "caller":
            return

        def transcriber_cb(event: transcription.Transcriber.Event):
            self._transcriber_cb(event, participant)

        transcriber = transcription.Transcriber(audio_track=track, callback=transcriber_cb)
        transcriber.start()

    def _transcriber_cb(self, event: transcription.Transcriber.Event, participant: livekit.Participant):
        if event.type == transcription.EVENT_TYPE_MONOLOGUE_STARTED:
            if self.state.type == states.StateType.DOING_NOTHING:
                self._set_state(states.State_Listening())
        elif event.type == transcription.EVENT_TYPE_MONOLOGUE_UPDATED:
            # Do nothing in this case for now
            pass
        elif event.type == transcription.EVENT_TYPE_MONOLOGUE_FINISHED:
            self.chat_gpt.add_message(Message(role=MessageRole.user, content=event.text))
        elif event.type == transcription.EVENT_TYPE_NO_SPEECH:
            # Start generating a response
            if self.state.type == states.StateType.LISTENING and event.time_seconds > 1.0:
                self._set_state(states.State_GeneratingResponse())

    def _set_state(self, state: states.State):
        if state.type == states.StateType.DOING_NOTHING:
            pass
        elif state.type == states.StateType.LISTENING:
            pass
        elif state.type == states.StateType.GENERATING_RESPONSE:
            if self.state.type != states.StateType.LISTENING:
                logging.warning("Unexpected state transition")
                return
            asyncio.create_task(self._state_generating_response())
        elif state.type == states.StateType.SPEAKING_RESPONSE:
            asyncio.create_task(self._state_speaking_response(state))

        self.state = state

    async def _state_generating_response(self):
        response = await self.chat_gpt.GenerateText(model='gpt-3.5-turbo')
        print(response)
        self._set_state(states.State_SpeakingResponse(text=response))

    async def _state_speaking_response(self, state: states.State_SpeakingResponse):
        self.chat_gpt.add_message(Message(role=MessageRole.assistant, content=state.text))
        self._set_state(states.State_DoingNothing())

    def should_process(
        self, track: livekit.TrackPublication, participant: livekit.Participant
    ) -> bool:
        return track.kind == 1