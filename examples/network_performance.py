"""Deterministic offline models for Chapter 1.4 network performance.

These models do NOT send packets or predict live Internet performance.
All bitrates use bits/s, timestamps and delays use seconds.
"""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
from math import isfinite
from typing import Sequence


def _positive(value: float, label: str) -> None:
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{label} must be finite and positive")


def transmission_seconds(packet_bits: int, rate_bps: float) -> float:
    """Serialization delay L/R; excludes propagation and queueing."""
    _positive(float(packet_bits), "packet size")
    _positive(rate_bps, "bitrate")
    return packet_bits / rate_bps


def propagation_seconds(distance_m: float, speed_mps: float) -> float:
    """Propagation delay distance/speed; excludes serialization."""
    if not isfinite(distance_m) or distance_m < 0:
        raise ValueError("distance must be finite and nonnegative")
    _positive(speed_mps, "signal speed")
    return distance_m / speed_mps


def end_to_end_seconds(
    packet_bits: int,
    rates_bps: Sequence[float],
    propagation_delays: Sequence[float],
    router_processing_delays: Sequence[float] = (),
    router_queueing_delays: Sequence[float] = (),
) -> float:
    """One packet over H store-and-forward links and H-1 intermediate routers.

    Every link contributes one serialization and one propagation delay.
    Each *intermediate router* optionally contributes processing and queueing.
    End-system application and host processing delays are excluded.
    """
    if not rates_bps:
        raise ValueError("at least one link is required")
    if len(rates_bps) != len(propagation_delays):
        raise ValueError("one propagation delay is required per link")
    routers = len(rates_bps) - 1
    if router_processing_delays and len(router_processing_delays) != routers:
        raise ValueError("one processing delay per intermediate router")
    if router_queueing_delays and len(router_queueing_delays) != routers:
        raise ValueError("one queueing delay per intermediate router")
    delays = list(propagation_delays) + list(router_processing_delays) + list(router_queueing_delays)
    if any(not isfinite(delay) or delay < 0 for delay in delays):
        raise ValueError("all supplied delays must be finite and nonnegative")
    return sum(transmission_seconds(packet_bits, rate) for rate in rates_bps) + sum(delays)


def traffic_intensity(arrival_packets_per_s: float, packet_bits: int, rate_bps: float) -> float:
    """Offered average bit rate divided by link service capacity, a*L/R."""
    if not isfinite(arrival_packets_per_s) or arrival_packets_per_s < 0:
        raise ValueError("arrival rate must be finite and nonnegative")
    _positive(float(packet_bits), "packet size")
    _positive(rate_bps, "bitrate")
    return arrival_packets_per_s * packet_bits / rate_bps


def md1_mean_queue_seconds(arrival_packets_per_s: float, packet_bits: int, rate_bps: float) -> float:
    """M/D/1 steady-state mean waiting, Poisson arrivals and fixed packet size.

    For rho >= 1 no finite steady-state mean exists in this infinite-buffer
    idealization. Finite-buffer routers instead drop or mark packets.
    """
    rho = traffic_intensity(arrival_packets_per_s, packet_bits, rate_bps)
    if rho >= 1:
        raise ValueError("M/D/1 stationary mean requires traffic intensity < 1")
    service_time = transmission_seconds(packet_bits, rate_bps)
    return rho * service_time / (2 * (1 - rho))


@dataclass(frozen=True)
class FifoResult:
    arrivals: int
    transmitted: int
    dropped: int
    waiting_seconds: tuple[float, ...]
    departure_seconds: tuple[float, ...]

    @property
    def loss_ratio(self) -> float:
        return self.dropped / self.arrivals if self.arrivals else 0.0

    @property
    def mean_wait_seconds(self) -> float:
        return sum(self.waiting_seconds) / self.transmitted if self.transmitted else 0.0


def simulate_fifo(
    arrivals_seconds: Sequence[float],
    packet_bits: int,
    rate_bps: float,
    *,
    waiting_capacity_packets: int | None = None,
) -> FifoResult:
    """One FIFO output link with deterministic per-packet service and tail drop.

    waiting_capacity_packets excludes the currently transmitting packet.
    Arrivals at exactly a completion timestamp see that completion first.
    No retransmission, ECN, AQM, variable packets, or propagation modeled.
    """
    service = transmission_seconds(packet_bits, rate_bps)
    if waiting_capacity_packets is not None and (
        not isinstance(waiting_capacity_packets, int) or
        isinstance(waiting_capacity_packets, bool) or
        waiting_capacity_packets < 0
    ):
        raise ValueError("waiting capacity must be a nonnegative integer or None")

    # Finish timestamps of accepted packets still in service or waiting.
    pending: deque[float] = deque()
    waits: list[float] = []
    departures: list[float] = []
    drops = 0
    previous = 0.0
    for t in arrivals_seconds:
        if not isfinite(t) or t < previous or t < 0:
            raise ValueError("arrival timestamps must be finite, nonnegative, sorted")
        previous = t
        while pending and pending[0] <= t:
            pending.popleft()
        if waiting_capacity_packets is not None and len(pending) >= waiting_capacity_packets + 1:
            drops += 1
            continue
        begin = max(t, pending[-1]) if pending else t
        done = begin + service
        pending.append(done)
        waits.append(begin - t)
        departures.append(done)
    return FifoResult(len(arrivals_seconds), len(waits), drops, tuple(waits), tuple(departures))


def bottleneck_upper_bound_bps(rates_bps: Sequence[float]) -> float:
    """Path capacity bound (ideal, no contention or overhead)."""
    if not rates_bps:
        raise ValueError("at least one link required")
    for rate in rates_bps:
        _positive(rate, "bitrate")
    return min(rates_bps)


def equal_share_upper_bound_bps(
    source_bps: float, destination_bps: float, shared_bps: float, concurrent_flows: int
) -> float:
    """Ideal equal sharing: min(source, destination, shared/n).

    Not a general Internet throughput guarantee; assumes n identical
    backlogged flows, equal capacity allocation, and no further bottlenecks.
    """
    for label, rate in (("source", source_bps), ("destination", destination_bps), ("shared", shared_bps)):
        _positive(rate, label)
    if not isinstance(concurrent_flows, int) or isinstance(concurrent_flows, bool) or concurrent_flows <= 0:
        raise ValueError("number of flows must be a positive integer")
    return min(source_bps, destination_bps, shared_bps / concurrent_flows)


def average_goodput_bps(delivered_payload_bits: int, duration_seconds: float) -> float:
    """Application payload delivery rate F/T, distinct from wire bit rate."""
    if not isinstance(delivered_payload_bits, int) or delivered_payload_bits < 0:
        raise ValueError("payload bits must be a nonnegative integer")
    _positive(duration_seconds, "duration")
    return delivered_payload_bits / duration_seconds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    delay = modes.add_parser("delay")
    delay.add_argument("--bits", type=int, required=True)
    delay.add_argument("--rates", type=float, nargs="+", required=True)
    delay.add_argument("--propagation", type=float, nargs="+", required=True)

    queue = modes.add_parser("queue")
    queue.add_argument("--bits", type=int, required=True)
    queue.add_argument("--rate", type=float, required=True)
    queue.add_argument("--arrivals", nargs="+", type=float, required=True)
    queue.add_argument("--capacity", type=int, default=None)

    share = modes.add_parser("share")
    share.add_argument("--source", type=float, required=True)
    share.add_argument("--destination", type=float, required=True)
    share.add_argument("--shared", type=float, required=True)
    share.add_argument("--flows", type=int, required=True)

    args = parser.parse_args(argv)
    if args.mode == "delay":
        print(f"{end_to_end_seconds(args.bits, args.rates, args.propagation):.6f} seconds")
    elif args.mode == "queue":
        result = simulate_fifo(args.arrivals, args.bits, args.rate, waiting_capacity_packets=args.capacity)
        print(f"accepted={result.transmitted}, dropped={result.dropped}, "
              f"mean_wait={result.mean_wait_seconds:.6f}s, loss={result.loss_ratio:.3f}")
    else:
        print(f"{equal_share_upper_bound_bps(args.source, args.destination, args.shared, args.flows):.0f} bits/s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
