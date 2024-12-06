# NetBox DHCP Export Automation

This project provides a setup for automatically exporting DHCP static bindings from [NetBox](https://github.com/netbox-community/netbox) to be used with the ISC DHCP server, ensuring consistent and up-to-date mappings.

#### Overview

The script (`netbox-export-dhcp.py`) retrieves MAC-IP address static bindings from NetBox (for devices and virtual entities) and updates the local DHCP configuration file. It is designed to run as a systemd service, periodically checking for updates to the DHCP bindings and reloading the DHCP server if any changes are detected.

#### Project Files

1. **`netbox-export-dhcp.py`**
   - **Purpose**: Main Python script to fetch DHCP reservations from NetBox.
   - **Functionality**:
     - Connects to NetBox using the REST API with an API token.
     - Retrieves IP address bindings designated for DHCP.
     - Safely writes DHCP entries to the local configuration file. If any changes to the configuration files are detected, it reloads the DHCP service.
     - Logs events via `syslog`.

2. **`netbox-export-dhcp.service`**
   - **Purpose**: Systemd service file for automating the script execution.
   - **Functionality**:
     - Defines a `simple` service that runs the Python script upon startup.
     - Restarts if it encounters issues, with a delay of 5 seconds between restarts.

3. **`netbox-export-dhcp.template`**
   - **Purpose**: NetBox export template for DHCP bindings.
   - **Functionality**:
     - Uses Jinja2 syntax to format output as an ISC DHCPD configuration file.
     - Output entries include a sequentially generated hostname, MAC address, and IP address. The device name is appended as an end-of-line comment for debugging purposes.

4. **`configuration_example.py`**
   - **Purpose**: Example configuration file.
   - **Configuration Parameters**:
     - `NETBOX_API_URL`: URL of the NetBox instance.
     - `NETBOX_API_TOKEN`: API token for accessing NetBox.
     - `OUTFILE`: Name of the output file for DHCP configurations.
     - `CONFDIR`: Directory where the DHCP configuration is stored (e.g., `/etc/dhcp`).

#### Installation and Usage

(Tested on AlmaLinux 9 with ISC DHCPD server)

1. **Prerequisites**
   - Clone this repository.
   - Install the required packages:
     ```bash
     dnf install dhcp-server python3-requests
     ```

2. **Configure the DHCP Server**
   - Include generated hosts in the `dhcpd.conf` by adding the following line:
     ```bash
     include "/etc/dhcp/dhcpd-netbox-hosts.conf";
     ```

3. **Setup NetBox**
   - **Add Template to NetBox**
     - Navigate to the **Customization** section and select **Export Templates**.
     - Fill in the required fields as follows:
       - **Name**: `dhcp_v2` (must be exactly as shown).
       - **Object types**: `IPAM > IP Address`.
       - **Template code**: Insert the contents of `netbox-export-dhcp.template`.
       - **File extension**: `.txt`.

     After saving the template, verify your settings in NetBox by navigating to **IPAM**, then **IP Addresses**. Click the **Export** button and select `dhcp_v2`. You should see the configured addresses displayed line by line.

4. **Setup Configuration**:
   - Copy `configuration_example.py` to `configuration.py`.
   - Update `configuration.py` with your NetBox API details, output file path, and DHCP configuration directory.

5. **Test the Setup by Running the Script Manually**
     - Execute the following command:
       ```bash
       python netbox-export-dhcp.py
       ```
     - The script should output the number of configured bindings. You can terminate the process with **Ctrl-C**.

6. **Install the Systemd Service**:
   - Place `netbox-export-dhcp.service` in `/etc/systemd/system/`.
   - Enable and start the service:
     ```bash
     sudo systemctl enable netbox-export-dhcp
     sudo systemctl start netbox-export-dhcp
     ```


#### Logging and Monitoring

Logs are directed to `syslog` for monitoring. Review logs with:
```bash
journalctl -u netbox-export-dhcp
```

#### Prerequisites

- **Python** and libraries: Ensure the required Python libraries are installed (e.g., `requests` for HTTP requests).
- **DHCP Server**: A DHCP service compatible with the generated configurations (e.g., `dhcpd`).
- **NetBox**: Ensure API access is configured and the necessary IP allocations are available.

#### Troubleshooting

- **Configuration Errors**: Verify the parameters in `configuration.py`.
- **Service Failures**: Check logs for details, especially for connectivity issues with NetBox or incorrect file paths.
