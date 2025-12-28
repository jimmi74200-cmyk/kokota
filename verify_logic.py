import sys
import unittest
from datetime import datetime, timedelta
from src.neo_client import NeoClientWrapper
from src.logic import get_atm_strike, calculate_stop_loss, get_current_weekly_expiry

class TestScalperLogic(unittest.TestCase):
    def setUp(self):
        self.config = {
            "credentials": {
                "mobile_number": "1234567890",
                "password": "pass",
                "mpin": "0000",
                "totp_secret": "JBSWY3DPEHPK3PXP"
            },
            "trading_settings": {
                "default_quantity": 50,
                "auto_sl_points": 10
            },
            "app_settings": {
                "use_mock_api": True
            }
        }
        self.client = NeoClientWrapper(self.config, use_mock=True)

    def test_login(self):
        print("Testing Login...")
        result = self.client.login()
        self.assertTrue(result)

    def test_atm_calculation(self):
        print("Testing ATM Calculation...")
        self.assertEqual(get_atm_strike(22020, 50), 22000)
        self.assertEqual(get_atm_strike(22030, 50), 22050)

    def test_expiry_calculation(self):
        print("Testing Expiry Calculation...")
        expiry = get_current_weekly_expiry()
        print(f"Calculated Expiry: {expiry}")
        self.assertTrue(len(expiry) > 5)

    def test_order_placement_and_price_fetch(self):
        print("Testing Order Placement and Price Fetch...")
        self.client.login()
        resp = self.client.place_order("NIFTY24APR22000CE", "B", "50")
        self.assertEqual(resp['stat'], "Ok")
        order_id = resp['nOrdNo']

        # Test get_filled_price mock
        price = self.client.get_filled_price(order_id)
        self.assertIsNotNone(price)
        self.assertTrue(price > 0)
        print(f"Fetched Price: {price}")

        # Simulate SL Trigger
        trigger = calculate_stop_loss(price, "B", 10)
        self.assertTrue(trigger < price)

    def test_cancel_all_orders(self):
        print("Testing Cancel All Orders...")
        self.client.login()

        # In mock, we don't really have "pending" orders easily without modifying place_order to be pending.
        # But we can verify the method exists and runs.
        resp = self.client.cancel_all_orders()
        self.assertEqual(resp['stat'], "Ok")
        print("Cancel All Orders Passed.")

    def test_panic_logic(self):
        print("Testing Panic Logic (Positions)...")
        self.client.login()
        self.client.place_order("NIFTY24APR22000CE", "B", "50")

        pos = self.client.get_positions()['data']
        for p in pos:
            qty = int(p['fldQty'])
            if qty != 0:
                side = "S" if qty > 0 else "B"
                self.client.place_order(p['trdSym'], side, str(abs(qty)))

        pos_after = self.client.get_positions()['data']
        target = next((p for p in pos_after if p['trdSym'] == "NIFTY24APR22000CE"), None)
        self.assertIsNone(target)

if __name__ == '__main__':
    unittest.main()
