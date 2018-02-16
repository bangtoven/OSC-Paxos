import argparse
import math

from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import osc_message_builder
from pythonosc import udp_client

from utils import process_state, read_state

def print_volume_handler(unused_addr, args, volume):
  print("[{0}] ~ {1}".format(args[0], volume))

def print_compute_handler(unused_addr, args, volume):
  try:
    print("[{0}] ~ {1}".format(args[0], args[1](volume)))
  except ValueError: pass

def am_i_leader(view_number, f, pid):
  leader_number = view_number % (2*f+1)
  return(pid == leader_number)

def promise(new_leader_id):


    

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--ip",
      default="127.0.0.1", help="The ip to listen on")
  parser.add_argument("--port",
      type=int, default=5005, help="The port to listen on")
  args = parser.parse_args()

  dispatcher = dispatcher.Dispatcher()
  dispatcher.map("/filter", print)
  dispatcher.map("/volume", print_volume_handler, "Volume")
  dispatcher.map("/logvolume", print_compute_handler, "Log volume", math.log)
  dispatcher.map("/dosomething", myfunction)
  dispatcher.map("/prepare", promise)

  process_states = read_state("config")
  # print(process_states[0].ip, process_states[0].port, process_states[0].pid)
  
  senders = []
  for s in process_states:
    temp = udp_client.SimpleUDPClient(s.ip, int(s.port))
    senders.append(temp)
  
  for sender in senders:
    sender.send_message("/volume", 0.5)

  server = osc_server.ThreadingOSCUDPServer((args.ip, args.port), dispatcher)
  server.serve_forever() # how to deal with this????

  # for very beginning
  if am_i_leader(v, f, p): # i am the leader
    for sender in senders:
      sender.send_message("/prepare", my_pid)
  else 

# print("Serving on {}".format(server.server_address))
  
  print("Am I getting here??")
  
  