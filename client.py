import argparse
import random
import time
import threading

from pythonosc import osc_message_builder
from pythonosc import udp_client, dispatcher, osc_server
from utils import read_state, sendMessageWithLoss
from message import Message
from record import Record
from threading import Lock

class ClientProcess:
  def __init__(self, cid, server_count, client_count, message_loss):
    if message_loss in range(0, 100):
      self.lossRate = message_loss / 100.0
    else:
      self.lossRate = 0.0

    self.mutex = Lock()
    self.cid = cid
    self.mid = -1
    self.batch_mode = True

    self.clientStates = read_state("clients_config", client_count)
    self.port = self.clientStates[self.cid].port
    self.processStates = read_state("servers_config", server_count)
    self.sendChannels = []
    for p in self.processStates:
      s = udp_client.SimpleUDPClient(p.ip, p.port)
      self.sendChannels.append(s)
    self.logRoundNumber = -1
    self.responses = {}

    self.view = -1
    self.received = False

  def start(self):  
    d = dispatcher.Dispatcher()
    d.map("/processResponse", self.processResponse_handler, "receivedMsg")
    d.map("/missingValue", self.missingValue_handler, "receivedMsg")

    listen = osc_server.ThreadingOSCUDPServer(("127.0.0.1", self.port), d)
    listeningThread = threading.Thread(target=listen.serve_forever)
    listeningThread.start()
    print("Client {} started.".format(self.cid))

    self.sendClientRequest()

  def sendMessageToEveryone(self, label, sendingMsg):
    print("Sending Client request: ", sendingMsg)
    for i,s in enumerate(self.sendChannels):
      sendMessageWithLoss(s, label, sendingMsg, self.lossRate)
      # s.send_message(label,sendingMsg)

  def processResponse_handler(self, addr, args, recievedMsg):
    print("\n"+addr)
    recieved = Record.fromString(recievedMsg)
    print("Returned: roundNumber: {} cid: {} message_value: {}".format(recieved.roundNumber, recieved.message.cid, recieved.message.value))
    print("lognumber:", self.logRoundNumber)
    if recieved.roundNumber not in self.responses:
      self.view = recieved.view
      self.responses[recieved.roundNumber] = recieved

    if self.logRoundNumber + 1 == recieved.roundNumber:
      self.mutex.acquire()
      try:
        self.logRoundNumber +=1
        self.addToLog(recieved)
      finally:
        self.mutex.release()
    elif self.logRoundNumber+1 < recieved.roundNumber:
      #self.askResponseFromServer()
      print("ask  response from server")
      roundNumberTemp = self.logRoundNumber+1
      while roundNumberTemp <= recieved.roundNumber:
        sendingMsg = "client\t{}\t{}".format(str(self.cid),str(roundNumberTemp))
        self.sendMessageToEveryone("/requestMissingValue", sendingMsg)
        roundNumberTemp +=1
        #elif logRoundNumber + 1

    if self.batch_mode and recieved.message.cid == self.cid and recieved.message.mid == self.mid:
        self.received = True
        time.sleep(0.5)
        self.sendClientRequest()

    #if self.batch_mode:
    #  self.sendClientRequest()


  def missingValue_handler(self, addr, args, recievedMsg):
    print("\n"+addr)
    recieved = Record.fromString(recievedMsg)
    if recieved.roundNumber not in self.responses:
      self.responses[recieved.roundNumber] = recieved
    if self.logRoundNumber + 1 == recieved.roundNumber:
      self.addToLog(recieved)
  
  def addToLog(self, recieved):
    with open("client_log_"+str(self.cid),'a') as f_in:
      f_in.write(str(recieved.roundNumber))
      f_in.write(" ")
      f_in.write(str(recieved.message.cid))
      f_in.write(": ")
      f_in.write(recieved.message.value)
      f_in.write("\n")
      #self.logRoundNumber +=1

  def sendClientRequest(self):
    self.received = False
    t = threading.Timer(3.0, self.checkReceived)
    t.start()

    label = "/clientRequest"
    value = input(str(self.cid) + ": ")
    self.mid += 1
    sendingMsg = Message(self.cid, self.mid, value)
    self.sendMessageToEveryone(label, sendingMsg.toString())

  def checkReceived(self):
      if self.received == False:
          self.sendMessageToEveryone("/leaderFaulty", self.view)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--cid", type=int, default=-1, help="the id of the client")
  parser.add_argument("--server_count", type=int, default=3, help="number of servers")
  parser.add_argument("--client_count", type=int, default=-1, help="number of clients")
  parser.add_argument("--message_loss", type=float, default=0.0, help="test5: randomly drop p%")
  args = parser.parse_args()

  client = ClientProcess(args.cid, args.server_count, args.client_count, args.message_loss)
  client.start()





