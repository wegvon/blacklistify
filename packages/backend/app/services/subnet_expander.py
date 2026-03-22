"""
Expands CIDR notation to individual IP addresses.
Supports sampling mode for large subnets.
"""

import ipaddress
import math


def cidr_to_ips(cidr: str) -> list[str]:
    """Expand a CIDR to all usable host IPs."""
    network = ipaddress.ip_network(cidr, strict=False)
    return [str(ip) for ip in network.hosts()]


def cidr_ip_count(cidr: str) -> int:
    """Return the number of usable host IPs in a CIDR."""
    network = ipaddress.ip_network(cidr, strict=False)
    return network.num_addresses - 2 if network.prefixlen < 31 else network.num_addresses


def sample_ips_from_cidr(cidr: str) -> list[str]:
    """
    Select representative sample IPs from a CIDR.

    Strategy:
      /24 → all 254 IPs (small enough)
      /22 → 1 IP per /24 block = 4 samples
      /20 → 1 IP per /24 block = 16 samples
      /16 → 1 IP per /24 block = 256 samples

    For each /24 block, picks the .1 address as representative.
    """
    network = ipaddress.ip_network(cidr, strict=False)
    prefix = network.prefixlen

    if prefix >= 24:
        # Small subnet — scan all hosts
        return [str(ip) for ip in network.hosts()]

    # For larger subnets, pick 1 representative per /24 block
    samples = []
    num_24_blocks = 2 ** (24 - prefix)

    for i in range(num_24_blocks):
        # Get the .1 address of each /24 block
        block_start = int(network.network_address) + (i * 256)
        representative = ipaddress.IPv4Address(block_start + 1)
        samples.append(str(representative))

    return samples


def split_into_batches(items: list, batch_size: int) -> list[list]:
    """Split a list into batches of given size."""
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
