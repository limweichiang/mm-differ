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
CMD_CONFIG_HIERARCHY = "show configuration node-hierarchy | include \"/\" | exclude \"Default-node is\"\n"
CMD_CONFIG_COMMITTED = "show configuration committed"
CMD_ENCRYPT_DISABLE = "encrypt disable\n"

# Setting up paramiko client connection and credentials checking
# Broken: Adding host key for new hosts to ~/.ssh/known_hosts
# Validate: Returning by SSHClient object by value; Not sure how safe this is.
def ssh_client_connect (host, user, passwd):
    ssh_client = paramiko.SSHClient()
    ssh_client.load_system_host_keys()
    ssh_auth_fail_max = 3
    ssh_fail_max = 3

    while ssh_auth_fail_max > 0 and ssh_fail_max > 0:
        try:
            ssh_client.connect(host, username=user, password=passwd)
            break
        except (paramiko.ssh_exception.SSHException) as se:
            #Paramiko's exception handling does everything with SSHException which is bonkers.
            if "not found in known_hosts" in str(se): # Intecept SSHException for unknown host key.
                ssh_fail_max = ssh_fail_max - 1

                while True:
                    add_unknown_host = input("Host " + host + " is not known. Do you want to add this host as a known host? (y/n) ")
                    if add_unknown_host.lower() == 'y':
                        print('Adding unknown host ' + host)
                        ssh_client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy)
                        break
                    elif add_unknown_host.lower() == 'n':
                        print('Not adding unknown host ' + host + ', quiting.')
                        exit (-1)
                    else:
                        print('Invalid Input.')
                        pass
            elif "Authentication failed" in str(se): # Intecept SSHException for Auth Fail, in spite of an ACTUAL exception existing for Auth Failed
                print('Authentication failed for ' + host + '.')
                user = input("Re-enter username for " + host + ": ")
                passwd = getpass.getpass("Re-enter password for " + host + ": ")
                ssh_auth_fail_max = ssh_auth_fail_max - 1
        except (paramiko.ssh_exception.AuthenticationException, paramiko.ssh_exception.BadHostKeyException) as oe:
            print(oe)
            exit(-1)
        except socket.error as e:
            print(e)
            exit(-1)

    if ssh_auth_fail_max == 0 or ssh_fail_max == 0:
        print("Too many SSH connect errors, quiting.")
        exit(-1)
    
    return ssh_client

def ssh_execute (channel, command, channel_timeout = 1):
    channel.sendall(command) # Future: Add except handling; otherwise current uncaught exception -> bail is acceptable.
    time.sleep(0.5) # Hold this amount of sleep time to allow target to react

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
        if re.search('^\([a-zA-Z0-9\-\_]*\) [\^\*]{0,2}\[[a-zA-Z0-9\-\_]*\] #', data, re.MULTILINE):
            break
    
    channel.settimeout(original_timeout)
    return data

# Remove the executed command and CLI prompt from output
def clean_output(output, command = ""):
    output = output.replace('\r', '')
    lines = output.splitlines(True)
    clean_output = []

    for l in lines:
        if re.search('^\([a-zA-Z0-9\-\_]*\) [\^\*]{0,2}\[[a-zA-Z0-9\-\_]*\] #', l):
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

mm1_host = args.first_mm.strip()
mm1_admin = args.admin.strip()

mm2_host = args.second_mm.strip()
mm2_admin = args.admin.strip()


# Connect to MM1
print("Connecting to MM1 - " + mm1_host + "...")
mm1_ssh_client = ssh_client_connect(mm1_host, user=mm1_admin, passwd=ssh_passwd)
mm1_ssh_channel = mm1_ssh_client.invoke_shell()
mm1_ssh_channel.set_combine_stderr(True)
# Enable pulling full config, and disabling of password hashing to minimize diff errors
ssh_execute(mm1_ssh_channel, CMD_CONFIG_NOPAGING)
ssh_execute(mm1_ssh_channel, CMD_ENCRYPT_DISABLE)

# Connect to MM2
print("Connecting to MM2 - " + mm2_host + "...")
mm2_ssh_client = ssh_client_connect(mm2_host, user=mm2_admin, passwd=ssh_passwd)
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


print("\nVerifying configuration hierarchy is identical across MMs...")
print(mm1_host, ":", mm1_config_nodes)
print(mm2_host, ":", mm2_config_nodes)

# Compare configuration hierarchy by ensuring like for like node match
if mm1_config_nodes == mm2_config_nodes:
    print("Successful")

else:
    print("Failed. Cannot proceed, quiting...")
    
    # Disconnect
    mm1_ssh_client.close()
    mm2_ssh_client.close()

    # Bail out...
    exit(-1)

print("\nVerifying configuration at each hierarchy level is consistent across MMs...")

# Intializing Config Store
mm1_config = {}
mm2_config = {}

# Recurse through nodes, store committed configuration
for i in mm1_config_nodes:
    mm1_data = ssh_execute(mm1_ssh_channel, CMD_CONFIG_COMMITTED + " " + i + '\n')
    mm1_config[i] = clean_output(mm1_data, CMD_CONFIG_COMMITTED)

for j in mm2_config_nodes:
    mm2_data = ssh_execute(mm2_ssh_channel, CMD_CONFIG_COMMITTED + " " + j + '\n')
    mm2_config[j] = clean_output(mm2_data, CMD_CONFIG_COMMITTED)

# We'll check based on hierarchy of MM1; We passed initial hirerarchy consistency checks, so this is dependable.
for key, value in mm1_config.items():
    print(" - Verifying config node", key, "is consistent... ", end='')

    if value == mm2_config[key]:
        print("Successful")
    else:
        print("Failed... Running diff to show differences")

        print(" -- \'-\' denote lines unique to", mm1_host)
        print(" -- \'+\' denote lines unique to", mm2_host)
        diff = difflib.Differ()
        cfg_delta = diff.compare(value.splitlines(True), mm2_config[key].splitlines(True))
        sys.stdout.writelines(cfg_delta)

# Disconnect
mm1_ssh_client.close()
mm2_ssh_client.close()
