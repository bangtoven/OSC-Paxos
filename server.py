import argparse
import math

from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import osc_message_builder
from pythonosc import udp_client
import threading

from utils import process_state, read_state

leader_pid = 0
view_number = 0
n = 3

def print_volume_handler(unused_addr, args, volume):
  print("[{0}] ~ {1}".format(args[0], volume))
def print_compute_handler(unused_addr, args, volume):
  try:
    print("[{0}] ~ {1}".format(args[0], args[1](volume)))
  except ValueError: pass

def should_i_be_leader(view_number, f, pid):
  leader_number = view_number % (2*f+1)
  return(pid == leader_number)

def send_i_am_leader(view_number, senders):
  for sender in senders:
    sender.send_message('/i_am_leader', view_number)

def i_am_leader_handler(unused_addr, args, new_view_number):
  if new_view_number > view_number:
     #accept you are leader
     old_view_number = view_number
     global view_number = new_view_number
     leader_pid = view_number % n   
     #leader = process_states[leader_pid]
     leader_sender = senders[leader_pid]
     leader_sender.send_message('/you_are_leader', my_previous_value, old_view_number)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--ip",
      default="127.0.0.1", help="The ip to listen on")
  parser.add_argument("--port",
      type=int, default=5005, help="The port to listen on")
  parser.add_argument("--pid",
      type=int, default=0, help="The pid")
  args = parser.parse_args()

  dispatcher = dispatcher.Dispatcher()
  dispatcher.map("/filter", print)
  dispatcher.map("/volume", print_volume_handler, "Volume")
  dispatcher.map("/logvolume", print_compute_handler, "Log volume", math.log)
  dispatcher.map("/i_am_leader", i_am_leader_handler)
  #dispatcher.map("/dosomething", myfunction)
  #dispatcher.map("/prepare", promise)

  process_states = read_state("config")
  global n = len(process_states)
  f = int((n - 1)/2)
  # print(process_states[0].ip, process_states[0].port, process_states[0].pid)
  
  senders = []
  #TODO remove yourself from the list
  for s in process_states:
    temp = udp_client.SimpleUDPClient(s.ip, s.port)
    senders.append(temp)
  
  for sender in senders:
    sender.send_message("/volume", 0.5)

  #server = osc_server.ThreadingOSCUDPServer((args.ip, args.port), dispatcher)
  #server.serve_forever() # how to deal with this????
  my_ip = "127.0.0.1"
  my_pid = args.pid
  my_port = process_states[my_pid].port
  server = osc_server.ForkingOSCUDPServer((my_ip, my_port), dispatcher)
  server_thread = threading.Thread(target=server.serve_forever)
  server_thread.start()


  """
  # for very beginning
  if am_i_leader(v, f, p): # i am the leader
    for sender in senders:
      sender.send_message("/prepare", my_pid)
  #else 

  # print("Serving on {}".format(server.server_address))
  """

  print("Am I getting here??")
  view_number = 0
  if should_i_be_leader(view_number, f, my_pid):
    send_i_am_leader(view_number, senders)
  
  #server.shutdown()
