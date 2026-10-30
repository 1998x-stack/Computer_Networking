"""Offline network-foundations models, all deterministic and side-effect-free."""

import contextlib
import io
import unittest

from examples.network_foundations import (
    circuit_seconds,
    is_rfc1918,
    longest_prefix_match,
    main,
    pipelined_completion_seconds,
    store_forward_seconds,
)


class NetworkFoundationsTests(unittest.TestCase):
    def test_private_ranges_are_scoped_not_globally_unique(self):
        for value in ("10.20.30.40", "172.16.0.1", "172.31.255.254", "192.168.1.8"):
            self.assertTrue(is_rfc1918(value))
        for value in ("172.32.0.1", "8.8.8.8", "2001:db8::1"):
            self.assertFalse(is_rfc1918(value))

    def test_longest_prefix_wins_even_when_default_route_listed_first(self):
        routes = [
            ("0.0.0.0/0", "default"),
            ("192.0.2.0/24", "broad"),
            ("192.0.2.128/25", "specific"),
        ]
        self.assertEqual(longest_prefix_match("192.0.2.145", routes), "specific")
        self.assertEqual(longest_prefix_match("192.0.2.14", routes), "broad")
        self.assertEqual(longest_prefix_match("203.0.113.1", routes), "default")

    def test_no_matching_route_and_address_family(self):
        self.assertIsNone(longest_prefix_match("203.0.113.5", [("10.0.0.0/8", "private")]))
        self.assertEqual(longest_prefix_match("2001:db8::10", [("2001:db8::/32", "v6")]), "v6")
        self.assertIsNone(longest_prefix_match("2001:db8::1", [("0.0.0.0/0", "v4")]))

    def test_ambiguous_next_hops_rejected(self):
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            longest_prefix_match("192.0.2.4", [("192.0.2.0/24", "a"), ("192.0.2.0/24", "b")])

    def test_one_router_two_links(self):
        self.assertAlmostEqual(store_forward_seconds(12000, [1_000_000, 1_000_000]), 0.024)
        self.assertAlmostEqual(
            store_forward_seconds(12000, [1_000_000, 1_000_000], [0.002, 0.002]),
            0.028,
        )

    def test_nonidentical_rates_and_pipeline(self):
        self.assertAlmostEqual(store_forward_seconds(12000, [1e6, 2e6]), 0.018)
        self.assertAlmostEqual(pipelined_completion_seconds(12000, 1e6, 2, 3), 0.048)

    def test_tdm_example(self):
        self.assertAlmostEqual(circuit_seconds(640_000, 1_536_000, 24, 0.5), 10.5)

    def test_reject_invalid_models(self):
        for action in (
            lambda: store_forward_seconds(0, [1e6]),
            lambda: store_forward_seconds(8, [0]),
            lambda: store_forward_seconds(8, [1e6], [-1]),
            lambda: store_forward_seconds(8, [1e6, 1e6], [0]),
            lambda: pipelined_completion_seconds(8, 1e6, 1, 0),
            lambda: circuit_seconds(8, 1e6, 0, 0),
        ):
            with self.subTest(action=action):
                with self.assertRaises(ValueError):
                    action()

    def test_cli_examples(self):
        for arguments, expected in [
            (["packet", "--bits", "12000", "--rates", "1000000", "1000000"], "0.024000 seconds"),
            (["circuit", "--bits", "640000", "--rate", "1536000", "--slots", "24", "--setup", "0.5"], "10.500000 seconds"),
            (["forward", "--address", "192.0.2.141", "--route", "192.0.2.0/24", "hopA", "--route", "192.0.2.128/25", "hopB"], "hopB"),
        ]:
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                self.assertEqual(main(arguments), 0)
            self.assertEqual(buffer.getvalue().strip(), expected)


if __name__ == "__main__":
    unittest.main()
