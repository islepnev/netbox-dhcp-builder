#!/usr/bin/env python3

import sys
import re
import argparse
from collections import defaultdict

# Configuration: Set the sort key to 'mac' or 'ip'
SORT_KEY = 'mac'  # Change to 'ip' if needed

def parse_dhcpd_conf(file_path):
    """
    Parses a dhcpd.conf file and extracts MAC-IP pairs.

    Returns:
        mac_to_ip: dict mapping MAC to IP
        ip_to_mac: dict mapping IP to MAC
        mac_to_line: dict mapping MAC to original line
        ip_to_line: dict mapping IP to original line
    """
    mac_to_ip = {}
    ip_to_mac = {}
    mac_to_line = {}
    ip_to_line = {}

    # Regular expressions to extract MAC and IP
    mac_regex = re.compile(r'hardware\s+ethernet\s+([0-9A-Fa-f:]+)\s*;')
    ip_regex = re.compile(r'fixed-address\s+([0-9.]+)\s*;')

    with open(file_path, 'r') as f:
        for line_number, line in enumerate(f, 1):
            # Remove comments
            line_no_comment = line.split('#')[0]
            mac_match = mac_regex.search(line_no_comment)
            ip_match = ip_regex.search(line_no_comment)

            if mac_match and ip_match:
                mac = mac_match.group(1).upper()
                ip = ip_match.group(1)
                mac_to_ip[mac] = ip
                ip_to_mac[ip] = mac
                mac_to_line[mac] = line.strip()
                ip_to_line[ip] = line.strip()
            else:
                # Line doesn't match expected format; ignore or handle as needed
                continue

    return mac_to_ip, ip_to_mac, mac_to_line, ip_to_line

def sort_ips(ip_list):
    """
    Sorts a list of IP addresses in ascending order.
    """
    return sorted(ip_list, key=lambda ip: tuple(int(part) for part in ip.split('.')))

def sort_macs(mac_list):
    """
    Sorts a list of MAC addresses in ascending order.
    """
    return sorted(mac_list)

def main():
    parser = argparse.ArgumentParser(description='Compare two dhcpd.conf files.')
    parser.add_argument('file1', help='First dhcpd.conf file path')
    parser.add_argument('file2', help='Second dhcpd.conf file path')
    args = parser.parse_args()

    # Parse both files
    mac_to_ip1, ip_to_mac1, mac_to_line1, ip_to_line1 = parse_dhcpd_conf(args.file1)
    mac_to_ip2, ip_to_mac2, mac_to_line2, ip_to_line2 = parse_dhcpd_conf(args.file2)

    # Create sets of (mac, ip) tuples
    set1 = set(mac_to_ip1.items())
    set2 = set(mac_to_ip2.items())

    # Calculate matching and missing pairs
    matching = set1 & set2
    missing_in_first = set2 - set1
    missing_in_second = set1 - set2

    # Calculate IP mismatches
    common_macs = set(mac_to_ip1.keys()) & set(mac_to_ip2.keys())
    ip_mismatches = []
    for mac in common_macs:
        ip1 = mac_to_ip1[mac]
        ip2 = mac_to_ip2[mac]
        if ip1 != ip2:
            ip_mismatches.append((mac, ip1, ip2))

    # Calculate MAC mismatches
    common_ips = set(ip_to_mac1.keys()) & set(ip_to_mac2.keys())
    mac_mismatches = []
    for ip in common_ips:
        mac1 = ip_to_mac1[ip]
        mac2 = ip_to_mac2[ip]
        if mac1 != mac2:
            mac_mismatches.append((ip, mac1, mac2))

    # Output missing lines
    print(f"Missing in {args.file1} (present in {args.file2}, not in {args.file1}):")
    if missing_in_first:
        missing_in_first_sorted = sort_ips([ip for mac, ip in missing_in_first])
        for ip in missing_in_first_sorted:
            # Find the corresponding MAC
            mac = ip_to_mac2.get(ip)
            if mac and (mac, ip) in missing_in_first:
                print(mac_to_line2[mac])
    else:
        print("None")
    print()

    print(f"Missing in {args.file2} (present in {args.file1}, not in {args.file2}):")
    if missing_in_second:
        missing_in_second_sorted = sort_ips([ip for mac, ip in missing_in_second])
        for ip in missing_in_second_sorted:
            # Find the corresponding MAC
            mac = ip_to_mac1.get(ip)
            if mac and (mac, ip) in missing_in_second:
                print(mac_to_line1[mac])
    else:
        print("None")
    print()

    # Output IP mismatches
    print(f"IP Mismatches (Same MAC, different IPs) between {args.file1} and {args.file2}:")
    if ip_mismatches:
        ip_mismatches_sorted = sorted(ip_mismatches, key=lambda x: x[0])  # Sort by MAC
        for mac, ip1, ip2 in ip_mismatches_sorted:
            print(f"MAC {mac}: {args.file1} has IP {ip1} vs {args.file2} has IP {ip2}")
    else:
        print("None")
    print()

    # Output MAC mismatches
    print(f"MAC Mismatches (Same IP, different MACs) between {args.file1} and {args.file2}:")
    if mac_mismatches:
        mac_mismatches_sorted = sorted(mac_mismatches, key=lambda x: tuple(int(part) for part in x[0].split('.')))  # Sort by IP
        for ip, mac1, mac2 in mac_mismatches_sorted:
            print(f"IP {ip}: {args.file1} has MAC {mac1} vs {args.file2} has MAC {mac2}")
    else:
        print("None")
    print()

    # Output summary
    print("Summary:")
    print(f"Matching pairs: {len(matching)}")
    print(f"Missing in {args.file1}: {len(missing_in_first)}")
    print(f"Missing in {args.file2}: {len(missing_in_second)}")
    print(f"IP mismatches: {len(ip_mismatches)}")
    print(f"MAC mismatches: {len(mac_mismatches)}")

if __name__ == "__main__":
    main()
