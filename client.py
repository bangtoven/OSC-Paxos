import argparse
import random
import time
import threading

from pythonosc import osc_message_builder
from pythonosc import udp_client, dispatcher, osc_server
from utils import read_state
from message import Message

class clientProcess:
  def __int__(self, cid):
    self.cid = cid
    self.mid = -1
    self.batch_mode = False

    self.clientStates = read_state("clients_config")
    self.port = self.clientStates[self.cid].port

    self.processStates = read_state("servers_config")
    self.sendChannels = []
    for p in processStates:
      s = udp_client.SimpleUDPClient(p.ip, p.port)
      self.sendChannels.append(s)

  def start(self):  
    d = dispatcher.Dispatcher()
    d.map("/processResponse", processResponse_handler, "receivedMsg")
  
    listen = osc_server.ThreadingOSCUDPServer(("127.0.0.1", self.port), d)
    listeningThread = threading.Thread(target=listen.serve_forever)
    listeningThread.start()
    print("Client {} started.".format(cid))

    self.sendClientRequest()

  def sendMessageToEveryone(self, label, sendingMsg, sendChannels):
    print("Sending Client request: ", sendingMsg)
    for i,s in enumerate(sendChannels):
      s.send_message(label,sendingMsg)

  def processResponse_handler(self, addr, args, receivedMsg):
    print("\n"+addr)
    parsed = receivedMsg.split("\t")
    view = parsed[0]
    roundNumber = parsed[1]
    cidMsg = parsed[2]
    message = parsed[3]
    print("Returned: roundNumber: {} cid: {} message: {}",format(roundNumber, cid, message))
    with open("client_log_"+str(self.cid),'a') as f_in:
      f_in.write(roundNumber)
      f_in.write(" ")
      f_in.write(cidMsg)
      f_in.write(": ")
      f_in.write(message)
      f_in.write("\n")
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
  args = parser.parse_args()

  cid = args.cid
  client = clientProcess(cid)
  client.start()





