import argparse
import random
import time
import threading

from pythonosc import osc_message_builder
from pythonosc import udp_client, dispatcher, osc_server
from utils import read_state



def sendMessageToEveryone(label, sendingMsg, sendChannels):
  print("Sending Client request: ", sendingMsg)
  for i,s in enumerate(sendChannels):
    s.send_message(label,sendingMsg)

def processResponse_handler(addr, args, receivedMsg):
  print("Returned, pid,  value: ", receivedMsg)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  #parser.add_argument("--ip", default="127.0.0.1",
  #    help="The ip of the OSC server")
  #parser.add_argument("--port", type=int, default=5005,
  #    help="The port the OSC server is listening on")
  parser.add_argument("--cid", type=int, default=-1, help="the id of the client")
  args = parser.parse_args()

  cid = args.cid
  clientStates = read_state("clients_config")
  port = clientStates[cid].port

  d = dispatcher.Dispatcher()
  d.map("/processResponse", processResponse_handler, "receivedMsg")
  
  listen = osc_server.ThreadingOSCUDPServer(("127.0.0.1", port), d)
  listeningThread = threading.Thread(target=listen.serve_forever)
  listeningThread.start()

  print("Client {} started.".format(cid))

  processStates = read_state("servers_config")
  sendChannels = []
  for p in processStates:
    s = udp_client.SimpleUDPClient(p.ip, p.port)
    sendChannels.append(s)

  label = "/clientRequest"
  value = random.randint(1,20)
  sendingMsg = "{}\t{}".format(str(cid), str(value))
  sendMessageToEveryone(label, sendingMsg, sendChannels)



