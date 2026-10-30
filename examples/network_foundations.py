"""Small, deterministic, offline demonstrations for Chapter 1, sections 1.1–1.3.

These are *models*, not a TCP/IP implementation or a packet sniffer.
All rates are in bits/second and all times are in seconds.
"""

from __future__ import annotations

import argparse
from ipaddress import ip_address, ip_network

RFC1918 = tuple(ip_network(block) for block in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"
))


def is_rfc1918(address: str) -> bool:
    """Check RFC 1918 IPv4 ranges (not the broader ipaddress.is_private flag)."""
    ip = ip_address(address)
    return ip.version == 4 and any(ip in network for network in RFC1918)


def longest_prefix_match(
    address: str, routes: list[tuple[str, str]]
) -> str | None:
    """Choose forwarding next-hop label from the longest matching prefix.

    Entries are (prefix, next_hop). This simplified lookup has no metric or
    ECMP tie breaking. Duplicate equally-specific matches are rejected.
    """
    ip = ip_address(address)
    candidates: list[tuple[int, str]] = []
    for prefix, next_hop in routes:
        network = ip_network(prefix, strict=False)
        if network.version == ip.version and ip in network:
            candidates.append((network.prefixlen, next_hop))
    if not candidates:
        return None
    best_length = max(length for length, _ in candidates)
    best = [hop for length, hop in candidates if length == best_length]
    if len(best) != 1:
        raise ValueError("Ambiguous longest-prefix match; provide distinct prefixes")
    return best[0]


def store_forward_seconds(
    packet_bits: int,
    link_rates_bps: list[float],
    propagation_seconds: list[float] | None = None,
) -> float:
    """One fully received packet across store-and-forward links.

    Assumptions: no queueing, no processing time, no retransmission, no
    cut-through switching. Per-hop serialization and propagation add up.
    """
    if packet_bits <= 0 or not link_rates_bps or any(rate <= 0 for rate in link_rates_bps):
        raise ValueError("Packet size and all link rates must be positive")
    delays = ([0.0] * len(link_rates_bps) if propagation_seconds is None
              else list(propagation_seconds))
    if len(delays) != len(link_rates_bps) or any(delay < 0 for delay in delays):
        raise ValueError("Need one nonnegative propagation delay per link")
    return sum(packet_bits / rate + delay for rate, delay in zip(link_rates_bps, delays))


def pipelined_completion_seconds(
    packet_bits: int, rate_bps: float, hops: int, packet_count: int
) -> float:
    """Completion time for fixed-size back-to-back packets on identical links.

    Ideal store-and-forward pipeline; excludes queueing, processing,
    propagation, headers, acknowledgements, and retransmissions.
    """
    if packet_bits <= 0 or rate_bps <= 0 or hops <= 0 or packet_count <= 0:
        raise ValueError("All parameters must be positive")
    return (hops + packet_count - 1) * packet_bits / rate_bps


def circuit_seconds(
    payload_bits: int, aggregate_rate_bps: float, slots: int, setup_seconds: float
) -> float:
    """Simple TDM model with one slot reserved per call and uniform links."""
    if payload_bits < 0 or aggregate_rate_bps <= 0 or slots <= 0 or setup_seconds < 0:
        raise ValueError("Invalid payload, capacity, slot count or setup delay")
    return setup_seconds + payload_bits / (aggregate_rate_bps / slots)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)

    packet = sub.add_parser("packet", help="One packet through store-and-forward hops")
    packet.add_argument("--bits", type=int, required=True)
    packet.add_argument("--rates", type=float, nargs="+", required=True)

    circuit = sub.add_parser("circuit", help="Reserved TDM-slot transfer model")
    circuit.add_argument("--bits", type=int, required=True)
    circuit.add_argument("--rate", type=float, required=True)
    circuit.add_argument("--slots", type=int, required=True)
    circuit.add_argument("--setup", type=float, default=0.0)

    forward = sub.add_parser("forward", help="Longest-prefix match demonstration")
    forward.add_argument("--address", required=True)
    forward.add_argument("--route", action="append", nargs=2, metavar=("PREFIX", "HOP"), required=True)

    args = parser.parse_args(argv)
    if args.operation == "packet":
        print(f"{store_forward_seconds(args.bits, args.rates):.6f} seconds")
    elif args.operation == "circuit":
        print(f"{circuit_seconds(args.bits, args.rate, args.slots, args.setup):.6f} seconds")
    elif args.operation == "forward":
        print(longest_prefix_match(args.address, args.route) or "no matching route")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
