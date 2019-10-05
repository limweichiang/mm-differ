import paramiko
import argparse
import getpass
import time
import socket
import sys
import string
import re
import difflib

CMD_CONFIG_NOPAGING = "no paging\n"
CMD_CONFIG_HIERARCHY = "show configuration node-hierarchy | include \"/\" | exclude is\n"
CMD_CONFIG_COMMITTED = "show configuration committed"
CMD_ENCRYPT_DISABLE = "encrypt disable\n"

#def ssh_client_connect (target, user, passwd):
#    paramiko.SSHClient()
#    mm1_ssh_client.load_system_host_keys()
#    mm1_ssh_client.connect(args.first_mm, username=args.admin, password=ssh_passwd)
#    mm1_stdin, mm1_stdout, mm1_stderr = mm1_ssh_client.exec_command(CMD_CONFIG_HIERARCHY)

def ssh_execute (channel, command, channel_timeout = 1):
    channel.sendall(command)
    time.sleep(0.5)

    data = ""

    original_timeout = channel.gettimeout()
    channel.settimeout(channel_timeout)

    while True:
        try:
            buffer = channel.recv(65535)
        except socket.timeout:
            break
        
        data += buffer.decode()
        
        # Check for CLI prompt; means command is completed so we don't have to wait for a timeout.
        if(re.search('^\([a-zA-Z0-9\-\_]*\) \[[a-zA-Z0-9\-\_]*\] #', data, re.MULTILINE)):
            break
    
    channel.settimeout(original_timeout)
    return data

# Remove the executed command and CLI prompt from output
def clean_output(output, command = ""):
    output = output.replace('\r', '')
    lines = output.splitlines(True)
    clean_output = []

    for l in lines:
        if re.search('^\([a-zA-Z0-9\-\_]*\) \[[a-zA-Z0-9\-\_]*\] #', l):
            pass
        elif command != "" and re.search(command, l):
            pass
        else:
            clean_output.append(l)

    return "".join(clean_output)

# Extract Configuration Hierarchy as a list of config nodes
def aos_get_cfg_nodes(output):
    cleaned_output = clean_output(output, CMD_CONFIG_HIERARCHY)
    #print(cleaned_output, end='')
    nodelines = cleaned_output.splitlines(True)

    clean_nodes = list()
    str_part_char = ""
    str_ignore = ""

    for nodeline in nodelines:
        node, str_part_char, str_ignore  = nodeline.partition(' ')
        clean_nodes.append(node)

    #print (clean_nodes)
    return clean_nodes


############################## Start main ##############################

parser = argparse.ArgumentParser(description="Aruba Mobility Master Configuration Hierarchy Comparator")
parser.add_argument("--first-mm", required=True, help="First Mobility Master")
parser.add_argument("--second-mm", required=True, help="Second Mobility Master")
parser.add_argument("--admin", required=True, help="Mobility Master admin user name")
args = parser.parse_args()

ssh_passwd = getpass.getpass("Password for " + args.admin +": ")

# Intializing Config Variables
mm1_config = {}
mm2_config = {}

mm1_host = args.first_mm.strip()
mm1_admin = args.admin.strip()

mm2_host = args.second_mm.strip()
mm2_admin = args.admin.strip()

# Connect to MM1
mm1_ssh_client = paramiko.SSHClient()
mm1_ssh_client.load_system_host_keys()
mm1_ssh_client.connect(args.first_mm, username=args.admin, password=ssh_passwd)
# Invoke Paramiko shell (needs error handling still)
mm1_ssh_channel = mm1_ssh_client.invoke_shell()
mm1_ssh_channel.set_combine_stderr(True)
# Enable pulling full config, and disabling of password hashing to minimize diff errors
ssh_execute(mm1_ssh_channel, CMD_CONFIG_NOPAGING)
ssh_execute(mm1_ssh_channel, CMD_ENCRYPT_DISABLE)

# Connect to MM2
mm2_ssh_client = paramiko.SSHClient()
mm2_ssh_client.load_system_host_keys()
mm2_ssh_client.connect(args.second_mm, username=args.admin, password=ssh_passwd)
# Invoke Paramiko shell (needs error handling still)
mm2_ssh_channel = mm2_ssh_client.invoke_shell()
mm2_ssh_channel.set_combine_stderr(True)
# Enable pulling full config, and disabling of password hashing to minimize diff errors
ssh_execute(mm2_ssh_channel, CMD_CONFIG_NOPAGING)
ssh_execute(mm2_ssh_channel, CMD_ENCRYPT_DISABLE)

# Pull configuration hierarchy & extract as config nodes
mm1_data = ssh_execute(mm1_ssh_channel, CMD_CONFIG_HIERARCHY)
mm1_config_nodes = aos_get_cfg_nodes(mm1_data)
mm1_config_nodes.sort()
mm2_data = ssh_execute(mm2_ssh_channel, CMD_CONFIG_HIERARCHY)
mm2_config_nodes = aos_get_cfg_nodes(mm2_data)
mm2_config_nodes.sort()


print("\nProceeding to verify configuration hierarchy is identical across MMs...")

# Compare configuration hierarchy by ensuring like for like node match
if mm1_config_nodes == mm2_config_nodes:
    print("- Verifying MM configuration hierarcy is identical: Successful")
    print(args.first_mm, ":", mm1_config_nodes)
    print(args.second_mm, ":", mm2_config_nodes)
else:
    print("- Verifying MM configuration hierarcy is identical: Failed")
    print("- Cannot proceed, exiting...")
    print(args.first_mm, ":", mm1_config_nodes)
    print(args.second_mm, ":", mm2_config_nodes)
    
    # Disconnect
    mm1_ssh_client.close()
    mm2_ssh_client.close()

    # Bail out...
    exit(-1)

print("\nProceeding to verify configuration at each hierarchy level is consistent across MMs...")

# Recurse through nodes, store committed configuration
for i in mm1_config_nodes:
    mm1_data = ssh_execute(mm1_ssh_channel, CMD_CONFIG_COMMITTED + " " + i + '\n')
    mm1_config[i] = clean_output(mm1_data, CMD_CONFIG_COMMITTED)

for j in mm2_config_nodes:
    mm2_data = ssh_execute(mm2_ssh_channel, CMD_CONFIG_COMMITTED + " " + j + '\n')
    mm2_config[j] = clean_output(mm2_data, CMD_CONFIG_COMMITTED)

for key, value in mm1_config.items():
    print(" - Verifying config node", key, "is consistent... ", end='')

    if value == mm2_config[key]:
        print("Successful")
    else:
        print("Failed... Running diff to show differences")

        print(" -- \'-\' denote lines unique to", args.first_mm)
        print(" -- \'+\' denote lines unique to", args.second_mm)
        diff = difflib.Differ()
        cfg_delta = diff.compare(value.splitlines(True), mm2_config[key].splitlines(True))
        sys.stdout.writelines(cfg_delta)

# Disconnect
mm1_ssh_client.close()
mm2_ssh_client.close()
