import os
import argparse
import time
import subprocess
import sys

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server_count", type=int, default=3, help="the number of servers")
    parser.add_argument("--client_count", type=int, default=2, help="the number of clients")
    parser.add_argument("--skipped_slot", type=int, default=-1, help="test4: force primary to skip for sequence x")
    parser.add_argument("--message_loss", type=int, default=0, help="test5: randomly drop p%. range(0,100)")
    parser.add_argument("--batch_mode", type=int, default=1, help="batch_mode")
    args = parser.parse_args()

    server_count = args.server_count
    client_count = args.client_count
    skipped_slot = args.skipped_slot
    message_loss = args.message_loss
    batch_mode = args.batch_mode

    cmd_args = " --server_count {} --client_count {} --skipped_slot {} --message_loss {} ".format(server_count, client_count, skipped_slot, message_loss)
    cmd_list = cmd_args.split()
    cmd_client_args = " --server_count {} --client_count {} --message_loss {} --batch_mode {}".format(server_count, client_count, message_loss, batch_mode)
    cmd_client_list = cmd_client_args.split()

    for i in reversed(range(server_count)): # reversed because pid 0 should be started last.
        subprocess.Popen(["python3","server.py","--pid",str(i)] + cmd_list )
        time.sleep(0.5)
        # server_run_cmd = server_run_cmd + "python3 server.py --pid " + str(i) + " --server_count " + str(server_count) +" --client_count " + str(client_count) + " &"
    time.sleep(1)

    for i in range(client_count):
        #client_run_cmd = client_run_cmd + "python3 client.py --cid " + str(i) + cmd_client_args + " & "
        subprocess.Popen(["python3","client.py","--cid",str(i)] + cmd_client_list )
        time.sleep(1)
        # client_run_cmd = client_run_cmd + "python3 client.py --cid " + str(i) + " --client_count " + str(client_count) + " --server_count " + str(server_count) + " &"

    #os.system(server_run_cmd)
    #time.sleep(2)
    os.system(client_run_cmd)
    #os.system("python3 server.py --pid 2 & python3 server.py --pid 1 & python3 server.py --pid 0")
