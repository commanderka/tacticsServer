from autobahn.twisted.websocket import WebSocketServerProtocol,WebSocketServerFactory
import json
import random
import sys

class ClientData:
    def __init__(self,clientString):
        self.clientString = clientString
        self.nSolvedPositions = 0
        self.nTimeForSolving = 0
        self.bestSolvingSpeed = sys.maxsize
    def toJson(self):
       return self.__dict__


class BroadcastServerFactory(WebSocketServerFactory):

    """
    Simple broadcast server broadcasting any message it receives to all
    currently connected clients.
    """

    def loadTacticPuzzles(self):
        puzzles = []
        puzzleFile = "mateIn2.txt"
        fileHandle = open(puzzleFile,"r")
        allLines = fileHandle.readlines()
        for currentLineIndex,currentLine in enumerate(allLines):
            if currentLine.startswith("1."):
                print (currentLineIndex)
                print(currentLine)
                print(len(puzzles))
                blackToMove = False    
                if currentLine.startswith("1..."):
                    blackToMove = True
                    currentLine=currentLine[4:]
                else:
                    currentLine= currentLine[2:]
                secondMoveIndex = currentLine.find("2.")
                firstMoveLine = currentLine[0:secondMoveIndex]
                firstMoveLine = firstMoveLine.strip()
                secondMoveLinePart = currentLine[secondMoveIndex+2:]
                secondMoveLinePart = secondMoveLinePart.strip()
                firstMoveLine_splitted = firstMoveLine.split(" ")
                secondMoveLine_splitted = secondMoveLinePart.split(" ")
                if blackToMove:
                    moveSequence = [firstMoveLine_splitted[0],secondMoveLine_splitted[0],secondMoveLine_splitted[1]]
                else:
                    moveSequence = [firstMoveLine_splitted[0],firstMoveLine_splitted[1],secondMoveLine_splitted[0]]
                fen = allLines[currentLineIndex-1].strip()
                splittedFen = fen.split(" ")
                if int(splittedFen[5]) <= 0:
                    splittedFen[5] = "1"
                fen = " ".join(splittedFen)
                jsonObject = {"type":"puzzle","content":{"id":currentLineIndex,"moveSequence":moveSequence,"fen":fen}}
                jsonString = json.dumps(jsonObject)
                puzzles.append(jsonString)
                print(moveSequence)
        return puzzles

    def __init__(self, url):
        #create tactic puzzles
        self.tacticPuzzles = self.loadTacticPuzzles()
        WebSocketServerFactory.__init__(self, url)
        self.clientMap = {}

    def register(self, client):
        if client.peer not in self.clientMap:
            print("registered client {}".format(client.peer))
            self.clientMap[client.peer] = ClientData(client.peer)

    def unregister(self, client):
        print("unregistered client {}".format(client.peer))

    def broadcast(self, msg):
        print("broadcasting message '{}' ..".format(msg))
        for c in self.clients:
            c.sendMessage(msg.encode('utf8'))
            print("message sent to {}".format(c.peer))

class MyServerProtocol(WebSocketServerProtocol):

    def __init__(self):
        super().__init__()
        self.nPuzzlesPerSession = 10
    def onConnect(self, request):
        print("Client connecting: {0}".format(request.peer))

    def onOpen(self):
        self.factory.register(self)
        self.sendHallOfFame()
        print("WebSocket connection open.")
    
    def sendHallOfFame(self):
        hallOfFame = list(self.factory.clientMap.values())
        for element in hallOfFame:
            print(element.toJson())
        hallOfFame.sort(key=lambda x: x.bestSolvingSpeed)
        hallOfFame_filtered = list(filter(lambda x:x.bestSolvingSpeed != sys.maxsize,hallOfFame))
        if len(hallOfFame_filtered) > 10:
            hallOfFame_filtered = hallOfFame_filtered[0:10]
        message = {}
        message["type"] = "hallOfFame"
        serializedHallOfFame = []
        for element in hallOfFame_filtered:
            serializedHallOfFame.append(element.toJson())
        message["content"] = serializedHallOfFame
        jsonString = json.dumps(message)
        self.sendMessage(jsonString.encode('utf-8'))

    def onMessage(self, payload, isBinary):
        if isBinary:
            print("Binary message received: {0} bytes".format(len(payload)))
        else:
            message = payload.decode('utf8')
            print("Text message received: {0}".format(message))
            print("Number of clients:{0}".format(len(self.factory.clientMap.keys())))
            if message.startswith('requestNewPosition'):
                 # echo back message verbatim
                randomPositionIndex = random.randint(0,len(self.factory.tacticPuzzles)-1)
                jsonString = self.factory.tacticPuzzles[randomPositionIndex]               
                self.sendMessage(jsonString.encode('utf-8'), False)
            elif message.startswith('setUserName'):
                 splittedMessage = message.split("_")
                 self.factory.clientMap[self.peer].sUserName = splittedMessage[1]
            elif message.startswith('solved'):
                splittedMessage = message.split("_")
                milliSecondsNeeded = splittedMessage[1]
                self.factory.clientMap[self.peer].nTimeForSolving += int(milliSecondsNeeded)
                self.factory.clientMap[self.peer].nSolvedPositions += 1
                #session ended
                if self.factory.clientMap[self.peer].nSolvedPositions == self.nPuzzlesPerSession:
                    messageString = json.dumps({"type":"sessionEnd"})              
                    self.sendMessage(messageString.encode('utf-8'), False)
                    self.factory.clientMap[self.peer].nSolvedPositions = 0
                    self.factory.clientMap[self.peer].solvingSpeed = self.factory.clientMap[self.peer].nTimeForSolving/self.nPuzzlesPerSession
                    if  self.factory.clientMap[self.peer].solvingSpeed < self.factory.clientMap[self.peer].bestSolvingSpeed:
                            self.factory.clientMap[self.peer].bestSolvingSpeed = self.factory.clientMap[self.peer].solvingSpeed
                    self.factory.clientMap[self.peer].nTimeForSolving = 0
                   
                    self.sendHallOfFame()

       

    def onClose(self, wasClean, code, reason):
        self.factory.unregister(self)
        print("WebSocket connection closed: {0}".format(reason))
        
    def connectionLost(self, reason):
        print("WebSocket connection lost: {0}".format(reason))
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)


if __name__ == '__main__':

    import sys

    from twisted.python import log
    from twisted.internet import reactor

    log.startLogging(sys.stdout)

    factory = BroadcastServerFactory(u"ws://127.0.0.1:9001")
    factory.protocol = MyServerProtocol
    # factory.setProtocolOptions(maxConnections=2)

    # note to self: if using putChild, the child must be bytes...

    reactor.listenTCP(9001, factory)
    reactor.run()
