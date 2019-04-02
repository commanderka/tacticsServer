from autobahn.twisted.websocket import WebSocketServerProtocol,WebSocketServerFactory
import json
import random

class BroadcastServerFactory(WebSocketServerFactory):

    """
    Simple broadcast server broadcasting any message it receives to all
    currently connected clients.
    """

    def loadTacticPuzzles(self):
        puzzles = []
        puzzleFile = "D:/coding/TacticsServer/mateIn2.txt"
        fileHandle = open(puzzleFile,"r")
        allLines = fileHandle.readlines()
        for currentLineIndex,currentLine in enumerate(allLines):
            if currentLine.startswith("1."):
                print (currentLineIndex)
                print(currentLine)
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
                jsonObject = {"id":currentLineIndex,"moveSequence":moveSequence,"fen":fen}
                jsonString = json.dumps(jsonObject)
                puzzles.append(jsonString)
                print(moveSequence)
        return puzzles

    def __init__(self, url):
        #create tactic puzzles
        self.tacticPuzzles = self.loadTacticPuzzles()
        WebSocketServerFactory.__init__(self, url)
        self.clients = []


    def register(self, client):
        if client not in self.clients:
            print("registered client {}".format(client.peer))
            self.clients.append(client)

    def unregister(self, client):
        if client in self.clients:
            print("unregistered client {}".format(client.peer))
            self.clients.remove(client)

    def broadcast(self, msg):
        print("broadcasting message '{}' ..".format(msg))
        for c in self.clients:
            c.sendMessage(msg.encode('utf8'))
            print("message sent to {}".format(c.peer))

class MyServerProtocol(WebSocketServerProtocol):

    def onConnect(self, request):
        print("Client connecting: {0}".format(request.peer))

    def onOpen(self):
        self.factory.register(self)
        print("WebSocket connection open.")

    def onMessage(self, payload, isBinary):
        if isBinary:
            print("Binary message received: {0} bytes".format(len(payload)))
        else:
            message = payload.decode('utf8')
            print("Text message received: {0}".format(message))
            print("Number of clients:{0}".format(len(self.factory.clients)))
            if (message=='requestNewPosition'):
                 # echo back message verbatim
                randomPositionIndex = random.randint(0,len(self.factory.tacticPuzzles))
                jsonString = self.factory.tacticPuzzles[randomPositionIndex]               
                self.sendMessage(jsonString.encode('utf-8'), False)

       

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