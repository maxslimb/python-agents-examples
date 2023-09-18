import logging
import asyncio
import livekit
import services.transcription as transcription
import services.tts as tts
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
        self.source = livekit.AudioSource(48000, 1)
        self.track = livekit.LocalAudioTrack.create_audio_track('kitt-audio', self.source)
        self.tts = tts.TTS(self.source, 48000, 1)
        asyncio.create_task(self.publish_audio())

    async def publish_audio(self):
        options = livekit.TrackPublishOptions()
        options.source = livekit.TrackSource.SOURCE_MICROPHONE
        await self.room.local_participant.publish_track(self.track, options)

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
            pass
        elif event.type == transcription.EVENT_TYPE_MONOLOGUE_FINISHED:
            self.chat_gpt.add_message(Message(role=MessageRole.user, content=event.text))
            if self.state.type == states.StateType.LISTENING:
                self._set_state(states.State_GeneratingResponse())
        elif event.type == transcription.EVENT_TYPE_NO_SPEECH:
            pass

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

        self.state = state

    async def _state_generating_response(self):
        resp = await self.chat_gpt.generate_text(model='gpt-3.5-turbo')
        await self.tts.generate_audio(resp)
        self.chat_gpt.add_message(Message(role=MessageRole.assistant, content=resp))
        self._set_state(states.State_DoingNothing())

    def should_process(
        self, track: livekit.TrackPublication, participant: livekit.Participant
    ) -> bool:
        return track.kind == 1
