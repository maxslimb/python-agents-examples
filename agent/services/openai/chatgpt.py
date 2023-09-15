import openai

class ChatGPT:
    async def GenerateText(self, prompt: str):
        return await openai.Completion.acreate(model='gpt4', prompt=prompt)