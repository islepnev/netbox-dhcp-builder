#!/usr/bin/env python

import os
import tempfile
import shutil
import logging
import logging.handlers
import re
import requests
import sys
import subprocess
import hashlib
import time
import tty
import configuration

logger = logging.getLogger(__name__)

last_hash = None


def setup_logging():
  # Configure logging to syslog
  logger.setLevel(logging.INFO)
  syslog_handler = logging.handlers.SysLogHandler(address = '/dev/log')
  formatter = logging.Formatter(fmt='%(module)s: %(message)s')
  syslog_handler.setFormatter(formatter)
  logger.addHandler(syslog_handler)
  if os.isatty(sys.stdout.fileno()):  # Check if stdout is a terminal
    stderr_handler = logging.StreamHandler(sys.stderr)
  #  stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)


def get_data():
  url = f"{configuration.NETBOX_API_URL}/api/ipam/ip-addresses"
  params = {"export": "dhcp_v1"}
  headers = {"Authorization": f"Token {configuration.NETBOX_API_TOKEN}"}

  try:
    api_timeout = 10
    response = requests.get(url, headers=headers, params=params, timeout=api_timeout)
    response.raise_for_status()  # Raises HTTPError if status code is 4xx or 5xx

    ctype = response.headers.get("content-type", "")
    if 'text/plain' not in ctype:
        raise ValueError(f"Unexpected content-type: {ctype}")

    logger.debug("NetBox API call succeeded.")
    return response.text

  except requests.exceptions.Timeout:
    logger.error("NetBox API call timed out.")
    raise

  except requests.exceptions.RequestException as e:
    logger.error(f"NetBox API call failed: {e}")
    raise


def write_temp_file(data, temp_dir):
    temp_fd, temp_path = tempfile.mkstemp(dir=temp_dir)
    try:
        with os.fdopen(temp_fd, 'w') as temp_file:
            temp_file.write(data)
        os.chmod(temp_path, 0o644)
        return temp_path
    except Exception as e:
        os.close(temp_fd)
        os.remove(temp_path)
        raise e


def reload_dhcpd():
  global last_hash

  # Check the DHCP configuration for errors
  try:
    cmd_check = ["dhcpd", "-t", "-user", "dhcpd", "-group", "dhcpd"]
    result = subprocess.run(cmd_check, capture_output=True, text=True)

    if result.returncode != 0:
      logger.error(f"Command '{' '.join(result.args)}' failed with exit code {result.returncode}:\n"
        f"{result.stderr.strip() if result.stderr is not None else 'No error message available'}")
      raise Exception("DHCP configuration check failed.")

    logger.debug("DHCP configuration check passed.")

    # Restart the dhcpd service
    subprocess.run(["systemctl", "restart", "dhcpd.service"], check=True)
    logger.info("dhcpd service restarted.")

  except subprocess.CalledProcessError as e:
    logger.error(f"Command '{e.cmd}' failed with exit code {e.returncode}: {e.stderr.strip()}")
    raise


def compute_file_hashes(conf_dir):
    """Compute the combined SHA256 hash of all dhcpd*.conf files."""
    hash_obj = hashlib.sha256()

    for filename in os.listdir(conf_dir):
        if filename.startswith("dhcpd") and filename.endswith(".conf"):
            file_path = os.path.join(conf_dir, filename)
            if os.path.isfile(file_path):
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                    hash_obj.update(file_data)

    return hash_obj.hexdigest()


def poll(conf_dir, target_path):
  global last_hash

  text = get_data()

  regex = re.compile(
    r"\s*host\s+\w+\s*{"
    r"\s*hardware\s+ethernet\s+[0-9a-fA-F:]+\s*;"
    r"\s*fixed-address\s+[0-9\.]+\s*;"
    r"\s*}\s*#*"
  )

  linecount = sum(bool(regex.search(line)) for line in text.split("\n"))
  if linecount < 1:
    raise Exception('No DHCP reservations in NetBox response, aborting')

  temp_path = write_temp_file(text, conf_dir)
  shutil.move(temp_path, target_path)
  logger.info(f"Updated {target_path}, {linecount} dhcp reservations")

  current_hash = compute_file_hashes(conf_dir)
  # Only process and reload dhcpd if the hash has changed
  if current_hash != last_hash:
    last_hash = current_hash  # Update the last hash
    reload_dhcpd()
  else:
    logger.debug("No changes detected in DHCP configuration, skipping dhcpd reload.")


def main():

  setup_logging()

  # Startup checks
  try:
    conf_dir = configuration.CONFDIR
    if not conf_dir:
      raise Exception('Configuration error: CONFDIR is not defined')
    if not os.path.exists(conf_dir):
      raise Exception('Configuration error: CONFDIR is not a directory')

    target_path = configuration.OUTFILE
    if not target_path:
      raise Exception('Configuration error: OUTFILE is not defined')
    if not target_path.startswith(conf_dir):
      target_path = os.path.join(conf_dir, target_path)

  except Exception as e:
    logger.error(f"{e}")
    sys.exit(1)

  # main loop
  while True:
    try:
      poll(conf_dir, target_path)
      time.sleep(30)

    except Exception as e:
      logger.error(f"{e}")
      sys.exit(1)


if __name__ == "__main__":
    main()
