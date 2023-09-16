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
    async def GenerateText(self, model: str, prompt: str, messages: [Message]):
        prompt_message = Message(role=MessageRole.system, content=prompt)
        res = await openai.ChatCompletion.acreate(model=model,
                                                  n=1,
                                                  messages=[prompt_message.toAPI()] + [m.toAPI() for m in messages])
        return res.choices[0].message.content
