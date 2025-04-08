# proxmox server
node = "pve"
server = ""
# API Token !!Manage Carefully!!
API_TOKEN = ''
headers = {
    'Authorization': API_TOKEN,
    'Content-Type': 'application/json'
}
#______________________________#
# Admin guacamole
guac_server = ""
guacamole_admin = "connector"
admin_password = "Vmware1!"
# Codice che identifica il qr code
key = ""
# Dir VM Guac
location = "ROOT" # ID root della cartella in guacamole
# Login User VM
VM_username = "guacamole"
VM_password = "Vmware1!"
