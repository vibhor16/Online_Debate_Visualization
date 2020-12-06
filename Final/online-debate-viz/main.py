from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pandas import DataFrame
from fastapi.responses import StreamingResponse
import io
from typing import Any, Dict
import json
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
NEUTRAL = "neutral"
DEMOCRAT = "democrat"
REPUBLICAN = "republican"

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:4200",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.neutral_active_connections: List[WebSocket] = []
        self.democrat_active_connections: List[WebSocket] = []
        self.republican_active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, tagger_type: str):
        await websocket.accept()
        if DEMOCRAT == tagger_type:
            self.democrat_active_connections.append(websocket)
        elif REPUBLICAN == tagger_type:
            self.republican_active_connections.append(websocket)
        else:
            self.neutral_active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket, tagger_type: str):
        if DEMOCRAT == tagger_type:
            self.democrat_active_connections.remove(websocket)
        elif REPUBLICAN == tagger_type:
            self.republican_active_connections.remove(websocket)
        else:
            self.neutral_active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: str, websocket: WebSocket, tagger_type: str):
        if DEMOCRAT == tagger_type:
            connections = self.democrat_active_connections
        elif REPUBLICAN == tagger_type:
            connections = self.republican_active_connections
        else:
            connections = self.neutral_active_connections

        for connection in connections:
            if connection != websocket:
                await connection.send_json(message)


manager = ConnectionManager()

idToNameMap = {"1": "Amy Klobuchar",
               "2": "Cory Booker",
               "3": "Pete Buttigieg",
               "4": "Bernie Sanders",
               "5": "Joseph R. Biden",
               "6": "Elizabeth Warren",
               "7": "Kamala Harris",
               "8": "Andrew Yang",
               "9": "Beto O'Rourke",
               "10": "Julián Castro"}

interactionList = []
interactionListDemocrat = []
interactionListRepublican = []
interactionListNeutral = []


@app.websocket("/ws/{tagger_type}")
async def websocket_endpoint(websocket: WebSocket, tagger_type: str):
    await manager.connect(websocket, tagger_type)
    try:
        while True:
            data = await websocket.receive_json()
            # print(data)
            # print("tagger_type: " + tagger_type)
            if type(data) is dict:
                # print(data['category'])
                if NEUTRAL == data['category']:
                    interactionList = interactionListNeutral
                elif DEMOCRAT == data['category']:
                    interactionList = interactionListDemocrat
                elif REPUBLICAN == data['category']:
                    interactionList = interactionListRepublican

                for d in data['democrats']:
                    for r in data['republican']:
                        interactionList.append([idToNameMap[d], idToNameMap[r], data['timestamp']])

            await manager.broadcast(f"{data}", websocket, tagger_type)
    except WebSocketDisconnect:
        manager.disconnect(websocket, tagger_type)
        await manager.broadcast(f"Client #{tagger_type} left the chat")


@app.get("/interactions/")
async def getInteractions(category: str):
    listToBeReturned = []
    if 'neutral' == category:
        print('neutral')
        listToBeReturned = interactionListNeutral
    elif 'democrat' == category:
        print('democrat')
        listToBeReturned = interactionListDemocrat
    elif 'republican' == category:
        print('republican')
        listToBeReturned = interactionListRepublican

    df = DataFrame(listToBeReturned, columns=['Attacker', 'Recipient', 'Time'])
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    response = StreamingResponse(iter([stream.getvalue()]),
                                 media_type="text/csv"
                                 )
    response.headers["Content-Disposition"] = "attachment; filename=export.csv"
    return response

#request: Dict[Any, Any]
@app.post("/saveFile/")
async def saveFile(data: Dict[Any, Any]):
    # print("hello!")
    # print(data)
    # path = "my.txt"
    # path = "C:/Users/gagan/Downloads/democrat/" + path
    out_file = open(data['path'], "w")
    json.dump(data['data'], out_file, indent=6)
    out_file.close()
    return data['path']

@app.get("/getFile/{path}")
async def getFile(path: str):
    path = "C:/Users/gagan/Downloads/democrat/" + path
    out_file = open(path, "r")
    my_dict = json.loads(out_file.read())
    return my_dict