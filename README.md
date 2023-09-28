# Python Agents

Example project demonstrating a number of different AI agents running in a python server environment using the new `client-sdk-python` from LiveKit

Fill out a .env file with the following in the agents/ directory

```
TOKEN_SERVICE_URL=http://localhost:3000
OPENAI_API_KEY=<api key to use ChatGPT>
ELEVENLABS_API_KEY=<api key for tts>
```

Run frontend
```
cd frontend
yarn dev
```

Run Agent Service
```
cd agent
python -m venv venv
source venv/bin/activate
python main.py
```
