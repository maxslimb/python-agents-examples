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
        self._message_capacity = message_capacity
        self._messages: [Message] = []

    def add_message(self, message: Message):
        self._messages.append(message)
        if len(self._messages) > self._message_capacity:
            self._messages.pop(0)

    async def generate_text(self, model: str):
        result = ""
        async for chunk in self.generate_text_streamed(model=model):
            result += chunk
        return result

    async def generate_text_streamed(self, model: str):
        prompt_message = Message(role=MessageRole.system, content=self._prompt)
        async for chunk in await openai.ChatCompletion.acreate(model=model,
                                                               n=1,
                                                               stream=True,
                                                               messages=[prompt_message.toAPI()] + [m.toAPI() for m in self._messages]):
            content = chunk["choices"][0].get("delta", {}).get("content")
            if content is not None:
                yield content
