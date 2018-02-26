import argparse
import random
import time
import threading

from pythonosc import osc_message_builder
from pythonosc import udp_client, dispatcher, osc_server
from utils import read_state
from message import Message
from record import Record

class ClientProcess:
  def __init__(self, cid, server_count, client_count):
    self.cid = cid
    self.mid = -1
    self.batch_mode = False

    self.clientStates = read_state("clients_config", client_count)
    self.port = self.clientStates[self.cid].port
    self.processStates = read_state("servers_config", server_count)
    self.sendChannels = []
    for p in self.processStates:
      s = udp_client.SimpleUDPClient(p.ip, p.port)
      self.sendChannels.append(s)
    self.logRoundNumber = -1
    self.responses = {}

  def start(self):  
    d = dispatcher.Dispatcher()
    d.map("/processResponse", self.processResponse_handler, "receivedMsg")

    listen = osc_server.ThreadingOSCUDPServer(("127.0.0.1", self.port), d)
    listeningThread = threading.Thread(target=listen.serve_forever)
    listeningThread.start()
    print("Client {} started.".format(self.cid))

    self.sendClientRequest()

  def sendMessageToEveryone(self, label, sendingMsg, sendChannels):
    print("Sending Client request: ", sendingMsg)
    for i,s in enumerate(sendChannels):
      s.send_message(label,sendingMsg)

  def processResponse_handler(self, addr, args, receivedMsg):
    print("\n"+addr)
    recieved = Record.fromString(receivedMsg)
    print("Returned: roundNumber: {} cid: {} message_value: {}".format(recieved.roundNumber, recieved.message.cid, recieved.message.value))
    if recieved.roundNumber not in self.responses:
      self.responses[recieved.roundNumber] = recieved
      if self.logRoundNumber + 1 == recieved.roundNumber:
        with open("client_log_"+str(self.cid),'a') as f_in:
            f_in.write(roundNumber)
            f_in.write(" ")
            f_in.write(cidMsg)
            f_in.write(": ")
            f_in.write(message)
            f_in.write("\n")
            self.logRoundNumber +=1
      else:
        #self.askResponseFromServer()
        print("ask  response from server")
    #elif logRoundNumber + 1 
      

    if self.batch_mode:
      self.sendClientRequest()

  def sendClientRequest(self):
    label = "/clientRequest"
    value = random.randint(1,20)
    self.mid += 1
    sendingMsg = Message(self.cid, self.mid, value)
    self.sendMessageToEveryone(label, sendingMsg.toString(), self.sendChannels)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--cid", type=int, default=-1, help="the id of the client")
  parser.add_argument("--server_count", type=int, default=3, help="number of servers")
  parser.add_argument("--client_count", type=int, default=-1, help="number of clients")
  args = parser.parse_args()

  client = ClientProcess(args.cid, args.server_count, args.client_count)
  client.start()





