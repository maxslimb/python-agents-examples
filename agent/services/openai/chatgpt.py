from dataclasses import dataclass
import openai
from enum import Enum

MessageRole = Enum('MessageRole', ["system", "user", "assistant", "function"])

@dataclass
class Message:
    role: MessageRole
    content: str

    def toAPI(self):
        return {
            "role": self.role.name,
            "content": self.content
        }


class ChatGPT:
    def __init__(self, prompt: str, message_capacity: int):
        self._prompt = prompt
        self._messages: [Message] = []

    def add_message(self, message: Message):
        self._messages.append(message)
        if len(self._messages) > 20:
            self._messages.pop(0)

    async def generate_text(self, model: str):
        prompt_message = Message(role=MessageRole.system, content=self._prompt)
        res = await openai.ChatCompletion.acreate(model=model,
                                                  n=1,
                                                  messages=[prompt_message.toAPI()] + [m.toAPI() for m in self._messages])
        return res.choices[0].message.content

    async def generate_text_streamed(self, model: str):
        prompt_message = Message(role=MessageRole.system, content=self._prompt)
        async for chunk in await openai.ChatCompletion.acreate(model=model,
                                                               n=1,
                                                               stream=True,
                                                               messages=[prompt_message.toAPI()] + [m.toAPI() for m in self._messages]):
            content = chunk["choices"][0].get("delta", {}).get("content")
            if content is not None:
                yield content
