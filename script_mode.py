import os
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server_count", type=int, default=3, help="the number of servers")
    parser.add_argument("--client_count", type=int, default=2, help="the number of clients")
    parser.add_argument("--skipped_slot", type=int, default=-1, help="test4: force primary to skip for sequence x")
    parser.add_argument("--message_loss", type=int, default=0, help="test5: randomly drop p%. range(0,100)")
    args = parser.parse_args()

    server_count = args.server_count
    client_count = args.client_count
    skipped_slot = args.skipped_slot
    message_loss = args.message_loss

    cmd_args = " --server_count {} --client_count {} --skipped_slot {} --message_loss {} ".format(server_count, client_count, skipped_slot, message_loss)

    server_run_cmd = ""
    client_run_cmd = ""
    for i in reversed(range(server_count)): # reversed because pid 0 should be started last.
        server_run_cmd = server_run_cmd + "python3 server.py --pid " + str(i) + cmd_args + " & "
        # server_run_cmd = server_run_cmd + "python3 server.py --pid " + str(i) + " --server_count " + str(server_count) +" --client_count " + str(client_count) + " &"

    for i in range(client_count):
        server_run_cmd = server_run_cmd + "python3 client.py --cid " + str(i) + cmd_args + " & "
        # client_run_cmd = client_run_cmd + "python3 client.py --cid " + str(i) + " --client_count " + str(client_count) + " --server_count " + str(server_count) + " &"

    os.system(server_run_cmd)
    os.system(client_run_cmd)
#os.system("python3 server.py --pid 2 & python3 server.py --pid 1 & python3 server.py --pid 0")
