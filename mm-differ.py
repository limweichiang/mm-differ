import paramiko
import argparse
import getpass




CMD_CONFIG_HIERARCHY = "show configuration node-hierarchy | include \"/\" | begin \"/\""
CMD_CONFIG_COMMITTED = "show configuration committed "
CMD_ENCRYPT_DISABLE = "encrypt disable"

#def ssh_client_connect (target, user, passwd):
#    paramiko.SSHClient()
#    mm1_ssh_client.load_system_host_keys()
#    mm1_ssh_client.connect(args.first_mm, username=args.admin, password=ssh_passwd)
#    mm1_stdin, mm1_stdout, mm1_stderr = mm1_ssh_client.exec_command(CMD_CONFIG_HIERARCHY)

#def diff_level ():


#def extract_config_hierarchy (msg, mm_config):


#def extract_config_committed (mm_config):

#def debug_explode_config (mm_config)):


parser = argparse.ArgumentParser(description="Aruba Mobility Master Configuration Hierarchy Comparator")
parser.add_argument("--first-mm", required=True, help="First Mobility Master")
parser.add_argument("--second-mm", required=True, help="Second Mobility Master")
parser.add_argument("--admin", required=True, help="Mobility Master admin user name")
args = parser.parse_args()

ssh_passwd = getpass.getpass("Password for " + args.admin +": ")



############################## Start main ##############################

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
mm1_stdin, mm1_stdout, mm1_stderr = mm1_ssh_client.exec_command(CMD_CONFIG_HIERARCHY)

print(mm1_stdin)
print(mm1_stdout)
print(mm1_stderr)

# Pull configuration hierarchy

# Extract configuration hierarchy as nodes
#extract_config_hierarchy(mm1_config)

# Recurse through nodes, store committed configuration
#extract_config_committed(mm1_config)

# Disconnect

# Connect to MM2
# Pull configuration hierarchy
# Extract configuration hierarchy as nodes
# Recurse through nodes, store committed configuration
# Disconnect


# Diff MM1 and MM2 Config, output differences