import os
import livekit
import aiohttp
import aiohttp_cors
import dotenv

from agents.transcription import Transcription
from agents.agent import Agent

dotenv.load_dotenv()


TOKEN_SERVICE_URL = os.environ.get("TOKEN_SERVICE_URL", "")
PORT = 8000

AGENTS: [Agent] = []

async def add_agent(request):
    data = await request.json()
    agent_type = data['agent']
    ws_url = ''
    token = ''
    async with aiohttp.ClientSession() as session:
        endpoint = f'{TOKEN_SERVICE_URL}/api/agent_connection_details?agent_type={agent_type}'

        async with session.get(endpoint) as response:
            json_response = await response.json()
            ws_url = json_response['ws_url']
            token = json_response['token']

    room = livekit.Room()
    if agent_type == 'transcription':
        print('A transcription agent is being added')
        await room.connect(ws_url, token)
        participant = room.local_participant
        transcription = Transcription(participant=participant, room=room)
        AGENTS.append(transcription)

    return aiohttp.web.json_response({'success': True})

app = aiohttp.web.Application()
app.add_routes([aiohttp.web.post('/add_agent', add_agent)])
cors = aiohttp_cors.setup(app, defaults={"*": aiohttp_cors.ResourceOptions(
    allow_credentials=True, expose_headers="*", allow_headers="*")})
for route in list(app.router.routes()):
    cors.add(route)

if __name__ == "__main__":
    aiohttp.web.run_app(app, port=PORT, host='0.0.0.0')
