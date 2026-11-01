"""Subnet arithmetic and input-validation tests, including RFC 3021 boundaries."""
import unittest
import subnet_calculator as calc


class SubnetCalculatorTests(unittest.TestCase):
    def test_host_network_and_mask(self):
        result = calc.calculate('192.168.1.76', 26)
        self.assertEqual(result['cidr'], '192.168.1.64/26')
        self.assertEqual(result['mask'], '255.255.255.192')
        self.assertEqual(result['wildcard'], '0.0.0.63')
        self.assertEqual(result['broadcast'], '192.168.1.127')
        self.assertEqual((result['first'], result['last']), ('192.168.1.65','192.168.1.126'))
        self.assertEqual((result['usable'], result['total']), (62, 64))

    def test_dotted_mask(self):
        self.assertEqual(calc.calculate('10.12.14.16', '255.255.255.0')['cidr'], '10.12.14.0/24')
        self.assertEqual(calc.calculate('10.12.14.16', '/20')['network'], '10.12.0.0')

    def test_host_routes_and_point_to_point(self):
        self.assertEqual(calc.calculate('203.0.113.17', 32)['usable'], 1)
        self.assertEqual(calc.calculate('203.0.113.17', 32)['first'], '203.0.113.17')
        self.assertEqual(calc.calculate('10.0.0.2', 31)['last'], '10.0.0.3')
        self.assertEqual(calc.calculate('10.0.0.2', 31)['usable'], 2)
        self.assertEqual(calc.calculate('0.0.0.0', 0)['total'], 4294967296)

    def test_reject_hostnames_ipv6_invalid_prefix_and_masks(self):
        for ip, prefix in [('example.com', 24), ('2001:db8::1', 64), ('10.0.0.1', 33),
                           ('10.0.0.1', -1), ('10.0.0.1', '255.0.255.0'),
                           ('10.0.0.1', True), ('10.0.0.1', '')]:
            with self.subTest(ip=ip,prefix=prefix), self.assertRaises(ValueError):
                calc.calculate(ip, prefix)

    def test_split_into_smaller_subnets(self):
        result = calc.split_subnets('192.168.1.0/24', '/26')
        self.assertEqual(result['count'], 4)
        self.assertEqual([r['cidr'] for r in result['rows']],
                         ['192.168.1.0/26', '192.168.1.64/26', '192.168.1.128/26', '192.168.1.192/26'])
        self.assertEqual(result['rows'][0]['usable'], 62)
        self.assertEqual(result['rows'][3]['range'], '192.168.1.193 – 192.168.1.254')

    def test_huge_split_bounded(self):
        result = calc.split_subnets('0.0.0.0/0', 32)
        self.assertEqual(result['count'], 4294967296)
        self.assertEqual(result['shown'], 128)
        self.assertTrue(result['truncated'])
        self.assertEqual(result['rows'][-1]['cidr'], '0.0.0.127/32')

    def test_invalid_split_prefix(self):
        for prefix in (23, 33, 'abc'):
            with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                calc.split_subnets('10.2.0.0/24', prefix)

    def test_summary_text(self):
        text = calc.summary_text(calc.calculate('10.2.3.4', 24))
        self.assertIn('Network: 10.2.3.0/24', text)
        self.assertIn('Usable addresses: 254', text)


if __name__ == '__main__':
    unittest.main()
