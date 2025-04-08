from config import node, server, headers, location, guac_server, VM_username, VM_password
import requests, urllib3 # Permette di fare richieste HTTP
import json, re, time, os
#from auth import session, guacamole_access
import auth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) # Disabilita i warning per i certificati non validi
base_url = f"https://{server}:8006/api2/json/nodes/{node}" # URL di base per le API di Proxmox
guac_url = f"http://{guac_server}:8080/guacamole/api/session/data/mysql" # URL di base per le API di Guacamole

# Controlli su hosts.json
# Se il file esiste ma è vuoto, lo inizializziamo con {}
file_path = "hosts.json"
if os.path.exists(file_path) and os.path.getsize(file_path) == 0:
    with open(file_path, "w") as f:
        json.dump({}, f, indent=4)
# Carica il file JSON esistente
with open('hosts.json', 'r') as f:
    try:
        hosts_data = json.load(f)
        if not isinstance(hosts_data, dict):  # Se il file non è valido, lo re-inizializziamo
            hosts_data = {}
    except json.JSONDecodeError:  # Se il JSON è corrotto o vuoto, lo re-inizializziamo
        hosts_data = {}

# Controlli su already.connected.json
# Se il file esiste ma è vuoto, lo inizializziamo con {}
second_file_path = "already_connected.json"
if os.path.exists(second_file_path) and os.path.getsize(second_file_path) == 0:
    with open(second_file_path, "w") as f:
        json.dump({}, f, indent=4)
# Carica il file JSON esistente
with open(second_file_path, 'r') as f:
    try:
        already_connected_data = json.load(f)
        if not isinstance(already_connected_data, dict):  # Se il file non è valido, lo re-inizializziamo
            already_connected_data = {}
    except json.JSONDecodeError:  # Se il JSON è corrotto o vuoto, lo re-inizializziamo
        already_connected_data = {}

def describe_errors(response):
    return response.status_code, response.text

def metodo(type, url, headers, data=None):
    if type == 'get':
        response = requests.get(url, headers=headers, verify=False)
    elif type == 'post':
        response = auth.session.post(url, headers=headers, json=data, verify=False)
    elif type == 'put':
        response = requests.put(url, headers=headers, json=data, verify=False)
    elif type == 'delete':
        response = requests.delete(url, headers=headers, verify=False)
    elif type == 'patch':
        response = requests.patch(url, headers=headers, json=data, verify=False)
    return response

def get_prox_VM():
    global vm_ids
    url = f"{base_url}/qemu"
    response = metodo('get', url, headers)
    if response.status_code == 200:
        vm_list = response.json()['data']
        vm_ids = [get_VM_info(vm['vmid']) for vm in vm_list if vm['vmid']] # Per ogni vmid che trova cerca le sue informazioni
    else:
        print(f"Error to retrieve vmid: {describe_errors(response)}")

def get_VM_info(vmid):
    global name
    if str(vmid) in hosts_data:
        return vmid
    url = f"{base_url}/qemu/{vmid}/config"
    response = metodo('get', url, headers)
    if response.status_code == 200:
        if 'template' in response.json()['data']:
            return # Se è un template non lo considera
        url = f"{base_url}/qemu/{vmid}/status/current"
        status_response = metodo('get', url, headers)
        json_data = status_response.json()["data"]["status"]
        if json_data != "running":
            return vmid# Se non è in esecuzione non lo considera
        name = response.json()['data']['name']
        print(f"Name: {name}")
        if 'ipconfig0' not in response.json()['data']: # Se non trova ipconfig0 cerca tramite guest-agent
            ip = get_IPvm(vmid)
            if ip is None: # Se la macchina non è accesa o non ottiene l'ip non viene salvata la config
                return vmid
            print(f"L'ip della {vmid}: è: {ip}")
            save_hosts_config(vmid)
            return vmid
        else:
            ip = response.json()['data']['ipconfig0']
            regex = r"ip=(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"

            match = re.search(regex, ip)
            if match:
                print(match.group(1))
            else:
                print("IP not match regex")
    else:
        print(f"Error to retrieve vmid: {describe_errors(response)}")

def get_IPvm(vmid, timeout=60):
    global ip_addr # variabile temporanea al posto del dhcp
    start_time = time.time()  # Registra l'ora di inizio
    print(f"Waiting for VM {vmid} IP...")
    while True:
        if time.time() - start_time > timeout: # timeout se non trova l'ip
            print("Unable to get VM IP after 2min")
            return None
        # Effettua la richiesta per ottenere le interfacce di rete della VM
        url = f"{base_url}/qemu/{vmid}/agent/network-get-interfaces"
        response = metodo('get', url, headers)
        if response.status_code == 200:
            json_response = response.json()
            interfaces = json_response.get('data', {}).get('result', [])
            if len(interfaces) < 2: # Se le interfacce sono minori di 2 vuol dire che è presente solo quella di loopback
                time.sleep(10)
            for item in interfaces:
                if 'lo' in item.get('name', '') or not item.get('ip-addresses', []) : # Se 'lo' o la scritta ip-addresses non esiste riprova
                    time.sleep(5)
                    continue
                else: 
                    for search_ipv4 in item.get('ip-addresses', []): # Se ip-addresses esiste ma l'ipè vuoto riprova
                        if search_ipv4.get('ip-address-type') != 'ipv4': # Se ip-addresses esiste ma l'ip è vuoto riprova
                            time.sleep(5)
                            continue
                        else:
                            ip_addr = search_ipv4['ip-address']
                            return ip_addr # se ottengo l'ip address vuol dire che la macchina parte
        else:
            time.sleep(5)

def save_hosts_config(vmid): # Salva le nuove configurazioni in hosts.json
    global hosts_data
    print(f"Saving VM {vmid} configuration...")
    hosts_data[vmid] = {
        "parentIdentifier": location,
        "name": name,
        "protocol": "rdp",
        "parameters": {
            "port": "3389",
            "ignore-cert":"true",
            "hostname": ip_addr,
            "username": VM_username,
            "password": VM_password
        },
    }
    # Infine scriviamo gli hosts
    with open(file_path, "w") as f:
        json.dump(hosts_data, f, indent=4)

def delete_config(vm_ids):
    # Elimina i None
    vm_ids = [vm_id for vm_id in vm_ids if vm_id is not None]

    # Converti entrambi a stringa nel momento del confronto
    to_delete = [vm_id for vm_id in hosts_data if str(vm_id) not in [str(x) for x in vm_ids]]
    if to_delete:
        print(f"VM IDs to delete: {to_delete}")
    # Elimina le configurazioni delle VM che non sono più presenti
    for vm_id in to_delete:
        print(f"Deleting VM {vm_id} configuration...")
        guac_id = already_connected_data[vm_id]
        url = f"{guac_url}/connections/{guac_id}"
        response = metodo('delete', url, guac_headers)

        if response.status_code == 200 or response.status_code == 204:
            print("Connection deleted successfully.")
        else:
            print(f"Error deleting connection: {describe_errors(response)}")
        del hosts_data[vm_id]
        del already_connected_data[vm_id]

    # Salva le modifiche nel file hosts.json
    with open(file_path, "w") as f:
        json.dump(hosts_data, f, indent=4)
    with open(second_file_path, "w") as f:
        json.dump(already_connected_data, f, indent=4)

def create_guac_json(base, update): # Crea il file json per guacamole
    for key, value in update.items():
        if isinstance(value, dict) and key in base:
            create_guac_json(base[key], value)
        else:
            base[key] = value
    return base

def create_connection(): # Crea la connessione in guacamole
    global already_connected_data, guac_headers
    with open('rdp_temp.json', 'r') as f:
            base_json = json.load(f)
            
    hosts = hosts_data.keys() # Estrae tutti gli hosts configurati
    for host_id in hosts: 
        if str(host_id) in str(already_connected_data.keys()): # Prima di fare le connessioni cerca se non esistono già in already_connected.json
            print(f"Host {host_id} already connected")
            continue  # salta se già connesso
        print(f"Eseguendo la connessione sulla macchina: {host_id}")
        body = create_guac_json(base_json, hosts_data[host_id])
        print("Creating connection...")

        url = f"{guac_url}/connections"
        response = metodo('post', url, guac_headers, body)
        if response.status_code == 200:
            print("Connections created successfully.")
            VM_id = get_guac_VM_ID(hosts_data[host_id]["name"])
            print(f"Saving VM id connection")
            save_connections(host_id, VM_id)
            asign_vm(hosts_data[host_id]["name"], VM_id)
        else:
            print(f"Error creating connection: {describe_errors(response)}")

def get_guac_VM_ID(hosts_name):
    url = f"{guac_url}/connections/"
    response = metodo('get', url, guac_headers)
    if response.status_code == 200:
        json_response = response.json()
        for vm in json_response.keys():
            # print(f"Looking in {vm}")
            if json_response[vm]['name'] == hosts_name:
                VM_id = json_response[vm]['identifier']
                return VM_id
        else:
            print(f"VM {hosts_name} not found in guacamole connections")
            return None
    else:
        print(f"Error to retrieve connectionGroups: {describe_errors(response)}")

def save_connections(host_id, VM_id):
    already_connected_data[host_id] = VM_id
    with open(second_file_path, "w") as f:
        json.dump(already_connected_data, f, indent=4)

def asign_vm(VM_name, id):
    with open('user_config.json', 'r') as f:
        user_config = json.load(f)

    for user, vms in user_config.items():
        if VM_name in vms:
             user_found = user
             break
    else:
        print(f"User {user} not found in user_config for vm {VM_name}")
        return

    urls = f"{guac_url}/users/{user_found}/permissions"
    vm = [{
        "op":"add",
        "path":f"/connectionPermissions/{id}",
        "value":"READ"
    }]

    response = metodo('patch', urls, guac_headers, vm)

    if response.status_code == 204:
        print(f"VM {VM_name} assigned to user {user}")
    else:
        print(f"Error assigning VM {VM_name} to user {user}: {describe_errors(response)}")

if __name__ == "__main__":
    get_prox_VM()
    GUAC_TOKEN = auth.guacamole_access()
    guac_headers = {
        'Guacamole-Token': GUAC_TOKEN,
        'Content-Type': 'application/json'
    }
    create_connection()
    delete_config(vm_ids)