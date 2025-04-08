# 🖥️ Proxmox ↔ Guacamole Auto Connector

This Python script automates the creation and management of **RDP connections** between virtual machines hosted on **Proxmox** and a **Guacamole** client.

Although the script is designed primarily for RDP, with minor adjustments, it can be extended to support other protocols.

---

## ⚙️ Configuration

All the necessary settings must be configured inside the [`config.py`](./config.py) file.

> 💡 **Important**: If you're using **TOTP-based 2FA** in Guacamole, you must also fill in the `key` field with the QR secret the first time you scan the code. If you don't have access to the TOTP key, there are two workarounds:
>
> 1. Create a new admin user and save the key upon first login.
> 2. From Guacamole settings, you should be able to reset the TOTP secret manually.

---

## 🔁 Script Behavior

This script is intended to be run **periodically** (e.g., via cron job or scheduler) to:

- ✅ **Sync** Proxmox VM configurations
- ➕ **Create new** connections for new VMs
- ❌ **Remove old** connections for VMs no longer present on Proxmox

To ensure it works correctly:

- Each VM must have the **QEMU Guest Agent** installed _or_ a **fixed IP configuration** via **Cloud-Init**
- The script fetches the IP address from the guest agent or static config

---

## 👥 User Assignment

The script reads from a `user_config.json` file to assign VMs to specific Guacamole users.

**Format:**

```json
{
  "username1": ["vm_name_1", "vm_name_2"],
  "username2": ["vm_name_3"]
}
```
## 📦 Requirements
pip install requests pyotp urllib3


