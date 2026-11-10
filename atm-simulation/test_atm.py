import os
import tempfile
import unittest

from atm import (ATM, CardBlocked, InsufficientFunds, InvalidPin,
                 InvalidAmount, LimitExceeded)


class ATMTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mktemp(suffix=".json")
        self.atm = ATM(self.tmp)

    def tearDown(self):
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def test_login_ok(self):
        self.assertEqual(self.atm.login("1001", "1234"), "Amit")

    def test_card_blocks_after_three_wrong_pins(self):
        for _ in range(2):
            with self.assertRaises(InvalidPin):
                self.atm.login("1001", "0000")
        with self.assertRaises(CardBlocked):
            self.atm.login("1001", "0000")
        with self.assertRaises(CardBlocked):
            self.atm.login("1001", "1234")

    def test_withdraw_and_notes(self):
        self.atm.login("1001", "1234")
        plan = self.atm.withdraw(2700)
        self.assertEqual(sum(d * n for d, n in plan.items()), 2700)
        self.assertEqual(self.atm.balance(), 47300)

    def test_insufficient_funds(self):
        self.atm.login("1002", "4321")
        with self.assertRaises(InsufficientFunds):
            self.atm.withdraw(15000)

    def test_daily_limit(self):
        self.atm.login("1001", "1234")
        with self.assertRaises(LimitExceeded):
            self.atm.withdraw(25000)

    def test_invalid_amounts(self):
        self.atm.login("1001", "1234")
        with self.assertRaises(InvalidAmount):
            self.atm.deposit(-5)
        with self.assertRaises(InvalidAmount):
            self.atm.withdraw(150)

    def test_transfer(self):
        self.atm.login("1001", "1234")
        self.atm.transfer("1002", 1000)
        self.assertEqual(self.atm.accounts["1002"].balance, 13000)


if __name__ == "__main__":
    unittest.main()
