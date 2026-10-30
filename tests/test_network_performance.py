"""Regression tests for offline P1-M2 network-performance models."""

from __future__ import annotations

import contextlib
import io
import unittest

from examples.network_performance import (
    average_goodput_bps,
    bottleneck_upper_bound_bps,
    end_to_end_seconds,
    equal_share_upper_bound_bps,
    main,
    md1_mean_queue_seconds,
    propagation_seconds,
    simulate_fifo,
    traffic_intensity,
    transmission_seconds,
)


class PerformanceTests(unittest.TestCase):
    def test_serialization_versus_propagation(self):
        self.assertAlmostEqual(transmission_seconds(12000, 1_000_000), 0.012)
        self.assertAlmostEqual(propagation_seconds(200_000, 2e8), 0.001)

    def test_router_count_is_links_minus_one(self):
        # Source -> R1 -> R2 -> Destination = 3 links, 2 routers.
        actual = end_to_end_seconds(
            12000, [1e6, 1e6, 1e6], [0.001, 0.001, 0.001],
            [0.002, 0.002], [0.003, 0.003]
        )
        self.assertAlmostEqual(actual, 0.049)
        self.assertAlmostEqual(end_to_end_seconds(8000, [1e6], [0.004]), 0.012)
        with self.assertRaisesRegex(ValueError, "processing"):
            end_to_end_seconds(8000, [1e6, 1e6], [0, 0], [0.1, 0.2])
        with self.assertRaisesRegex(ValueError, "propagation"):
            end_to_end_seconds(8000, [1e6, 1e6], [0])
        with self.assertRaises(ValueError):
            end_to_end_seconds(8000, [], [])

    def test_traffic_intensity_and_md1_assumptions(self):
        self.assertAlmostEqual(traffic_intensity(80, 10_000, 1e6), 0.8)
        self.assertAlmostEqual(md1_mean_queue_seconds(80, 10_000, 1e6), 0.02)
        self.assertAlmostEqual(md1_mean_queue_seconds(95, 10_000, 1e6), 0.095)
        self.assertEqual(md1_mean_queue_seconds(0, 10_000, 1e6), 0.0)
        for arrivals in (100, 101):
            with self.subTest(arrivals=arrivals):
                with self.assertRaisesRegex(ValueError, "requires"):
                    md1_mean_queue_seconds(arrivals, 10_000, 1e6)

    def test_fifo_burst_and_loss_at_capacity_one(self):
        # Each 1000-bit packet takes 1 sec at 1000 bits/s;
        # one in transmission plus one waiting slot.
        result = simulate_fifo([0, 0, 0, 1, 1], 1000, 1000, waiting_capacity_packets=1)
        self.assertEqual((result.arrivals, result.transmitted, result.dropped), (5, 3, 2))
        self.assertEqual(result.waiting_seconds, (0, 1, 1))
        self.assertEqual(result.departure_seconds, (1, 2, 3))
        self.assertAlmostEqual(result.loss_ratio, 0.4)
        self.assertAlmostEqual(result.mean_wait_seconds, 2 / 3)

    def test_zero_waiting_slots_and_instant_completion_priority(self):
        result = simulate_fifo([0, 0, 1, 1], 1000, 1000, waiting_capacity_packets=0)
        self.assertEqual((result.transmitted, result.dropped), (2, 2))
        self.assertEqual(result.waiting_seconds, (0.0, 0.0))

    def test_bursts_can_queue_even_if_average_rate_is_low(self):
        result = simulate_fifo([0, 0, 0, 100], 1000, 1000)
        self.assertEqual(result.dropped, 0)
        self.assertEqual(result.waiting_seconds, (0, 1, 2, 0))
        self.assertEqual(result.mean_wait_seconds, 0.75)

    def test_empty_arrivals(self):
        result = simulate_fifo([], 1000, 1000, waiting_capacity_packets=0)
        self.assertEqual(result.arrivals, 0)
        self.assertEqual(result.loss_ratio, 0)
        self.assertEqual(result.mean_wait_seconds, 0)

    def test_reject_invalid_parameters(self):
        failing = (
            lambda: transmission_seconds(0, 1),
            lambda: transmission_seconds(8, 0),
            lambda: propagation_seconds(-1, 2e8),
            lambda: propagation_seconds(1, 0),
            lambda: traffic_intensity(-2, 1000, 1e6),
            lambda: simulate_fifo([2, 1], 1000, 1000),
            lambda: simulate_fifo([float("nan")], 1000, 1000),
            lambda: simulate_fifo([0], 1000, 1000, waiting_capacity_packets=-1),
            lambda: bottleneck_upper_bound_bps([]),
            lambda: equal_share_upper_bound_bps(10, 10, 10, 0),
            lambda: average_goodput_bps(1, 0),
        )
        for fn in failing:
            with self.subTest(case=repr(fn)):
                with self.assertRaises(ValueError):
                    fn()

    def test_bottleneck_bound_and_equal_share(self):
        self.assertEqual(bottleneck_upper_bound_bps([8e6, 2e6, 10e6]), 2e6)
        self.assertEqual(equal_share_upper_bound_bps(10e6, 10e6, 5e6, 10), 500_000)
        self.assertEqual(equal_share_upper_bound_bps(300_000, 10e6, 5e6, 10), 300_000)
        self.assertEqual(average_goodput_bps(1_000_000, 2), 500_000)

    def test_cli_offline_examples(self):
        cases = (
            (
                ["delay", "--bits", "12000", "--rates", "1000000", "1000000",
                 "--propagation", "0.001", "0.001"],
                "0.026000 seconds",
            ),
            (
                ["queue", "--bits", "1000", "--rate", "1000", "--arrivals",
                 "0", "0", "0", "1", "1", "--capacity", "1"],
                "accepted=3, dropped=2, mean_wait=0.666667s, loss=0.400",
            ),
            (
                ["share", "--source", "10000000", "--destination", "10000000",
                 "--shared", "5000000", "--flows", "10"],
                "500000 bits/s",
            ),
        )
        for arguments, expected in cases:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(arguments), 0)
            self.assertEqual(output.getvalue().strip(), expected)


if __name__ == "__main__":
    unittest.main()
