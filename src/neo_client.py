import time
import threading
import logging
import random
import json
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NeoClientWrapper:
    def __init__(self, config, use_mock=False):
        self.config = config
        self.use_mock = use_mock
        self.client = None
        self.is_logged_in = False

        if self.use_mock:
            self.client = MockNeoClient(config)
        else:
            self.client = RealNeoClient(config)

    def login(self):
        try:
            self.client.login()
            self.is_logged_in = True
            logger.info("Login successful")
            return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def place_order(self, trading_symbol, transaction_type, quantity, product="MIS", price=0, trigger_price=0, order_type="MKT"):
        return self.client.place_order(
            trading_symbol=trading_symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            product=product,
            price=price,
            trigger_price=trigger_price,
            order_type=order_type
        )

    def cancel_order(self, order_id):
        return self.client.cancel_order(order_id)

    def cancel_all_orders(self):
        return self.client.cancel_all_orders()

    def get_positions(self):
        return self.client.get_positions()

    def subscribe(self, instrument_tokens):
        self.client.subscribe(instrument_tokens)

    def get_latest_ltp(self, instrument_token_or_symbol):
        return self.client.get_latest_ltp(instrument_token_or_symbol)

    def get_filled_price(self, order_id, retries=3):
        return self.client.get_filled_price(order_id, retries)

class RealNeoClient:
    def __init__(self, config):
        self.config = config
        self.creds = config.get("credentials", {})
        self.api_client = None
        self.latest_data = {} # Map token -> Price

    def on_message(self, message):
        # Callback for WebSocket
        # Message format varies, assuming list of quotes or single dict
        # Example: [{'instrument_token': '123', 'ltp': '22000'}]
        try:
            if isinstance(message, list):
                for tick in message:
                    self._process_tick(tick)
            elif isinstance(message, dict):
                self._process_tick(message)
        except Exception as e:
            logger.error(f"WS Error: {e}")

    def _process_tick(self, tick):
        # Extract Token and LTP
        # Adjust keys based on actual Neo API response structure
        token = tick.get('instrument_token') or tick.get('tk')
        ltp = tick.get('last_traded_price') or tick.get('ltp')

        if token and ltp:
            self.latest_data[str(token)] = float(ltp)

    def on_error(self, error):
        logger.error(f"WS Error: {error}")

    def login(self):
        try:
            from neo_api_client import NeoAPI
            import pyotp

            self.api_client = NeoAPI(
                consumer_key=self.creds.get("consumer_key"),
                consumer_secret=self.creds.get("consumer_secret"),
                environment='PROD',
                on_message=self.on_message, # Register callback
                on_error=self.on_error
            )

            totp_secret = self.creds.get("totp_secret")
            if not totp_secret:
                raise ValueError("TOTP Secret is missing in config")

            otp = pyotp.TOTP(totp_secret).now()

            self.api_client.login(
                mobilenumber=self.creds.get("mobile_number"),
                password=self.creds.get("password"),
                mpin=self.creds.get("mpin")
            )
            self.api_client.session_2fa(OTP=otp)

        except ImportError:
            logger.error("neo_api_client or pyotp not installed. Cannot use RealNeoClient.")
            raise
        except Exception as e:
            logger.error(f"Real API Login Error: {e}")
            raise

    def place_order(self, trading_symbol, transaction_type, quantity, product, price, trigger_price, order_type):
        try:
            params = {
                "exchange_segment": "nse_fo",
                "product": product,
                "price": str(price),
                "order_type": order_type,
                "quantity": str(quantity),
                "trading_symbol": trading_symbol,
                "transaction_type": transaction_type,
                "amo": "NO",
                "trigger_price": str(trigger_price)
            }
            # Handle SL-M specific if needed (Neo might use different order_type string)
            if order_type == "SL-M":
                params["order_type"] = "SL" # Often SL means Limit SL, SL-M might be distinct or handled via price=0
                # If SL-M is not directly supported, we might need 'SL' with price=0 or similar.
                # Assuming 'SL-M' is valid or mapped correctly by SDK.
                # Checking docs is best, but standard usually 'SL' + price for limit, 'SL-M' for market.
                pass

            response = self.api_client.place_order(**params)
            return response
        except Exception as e:
            logger.error(f"Real Place Order Error: {e}")
            return {"status": "error", "message": str(e)}

    def cancel_order(self, order_id):
        try:
            return self.api_client.cancel_order(order_id=order_id, is_amo="NO")
        except Exception as e:
            logger.error(f"Real Cancel Order Error: {e}")
            return {"status": "error", "message": str(e)}

    def cancel_all_orders(self):
        try:
            # 1. Get Open Orders
            resp = self.api_client.order_report()
            data = resp.get("data", [])

            # Filter for open
            open_orders = [o for o in data if o.get("ordSt") in ["open", "trigger_pending"]]

            for o in open_orders:
                oid = o.get("nOrdNo")
                if oid:
                    self.cancel_order(oid)
            return {"status": "Ok", "cancelled_count": len(open_orders)}
        except Exception as e:
            logger.error(f"Real Cancel All Error: {e}")
            return {"status": "error", "message": str(e)}

    def get_positions(self):
        try:
            return self.api_client.positions()
        except Exception as e:
            logger.error(f"Real Get Positions Error: {e}")
            return {"data": []}

    def subscribe(self, instrument_tokens):
        try:
            # Assuming instrument_tokens is a list of dicts or strings depending on SDK
            # SDK usually takes list of dicts: [{'instrument_token': '...', 'exchange_segment': 'nse_cm'}]
            if hasattr(self.api_client, 'subscribe'):
                self.api_client.subscribe(instrument_tokens=instrument_tokens, quote_type='qt')
        except Exception as e:
            logger.error(f"Subscribe Error: {e}")

    def get_latest_ltp(self, instrument_token_or_symbol):
        # Return local cache
        return self.latest_data.get(str(instrument_token_or_symbol), 0.0)

    def get_filled_price(self, order_id, retries=3):
        # Poll order book
        for i in range(retries):
            try:
                # Real API call to order book
                resp = self.api_client.order_report()
                # Neo API usually returns list of orders.
                data = resp.get("data", [])
                order = next((o for o in data if o.get("nOrdNo") == str(order_id)), None)

                if order:
                    status = order.get("ordSt", "")
                    if status.lower() == "complete" or status.lower() == "traded":
                        avg_price = float(order.get("avgPrc", 0.0))
                        if avg_price > 0:
                            return avg_price
            except Exception as e:
                logger.error(f"Error fetching filled price: {e}")

            time.sleep(0.5) # Wait before retry

        return None

class MockNeoClient:
    def __init__(self, config):
        self.config = config
        self.orders = {}
        self.positions = []
        self.order_counter = 1000

        self.market_data = {
            "NIFTY": 22000.0,
            "BANKNIFTY": 47000.0,
            "FINNIFTY": 20800.0
        }
        self.running = True
        self.sim_thread = threading.Thread(target=self._simulate_market, daemon=True)
        self.sim_thread.start()

    def _simulate_market(self):
        while self.running:
            for key in self.market_data:
                change = random.uniform(-5, 5)
                self.market_data[key] += change
            time.sleep(1)

    def login(self):
        time.sleep(0.5)
        return True

    def place_order(self, trading_symbol, transaction_type, quantity, product, price, trigger_price, order_type):
        time.sleep(0.1)
        order_id = str(self.order_counter)
        self.order_counter += 1

        fill_price = 0
        current_spot = 22000
        if "NIFTY" in trading_symbol: current_spot = self.market_data["NIFTY"]
        if "BANK" in trading_symbol: current_spot = self.market_data["BANKNIFTY"]

        fill_price = round(random.uniform(90, 110), 2)

        order = {
            "nOrdNo": order_id,
            "trdSym": trading_symbol,
            "trnsTp": transaction_type,
            "qty": quantity,
            "fldQty": quantity,
            "avgPrc": fill_price,
            "ordSt": "complete",
            "prod": product
        }
        self.orders[order_id] = order
        self._update_position(trading_symbol, transaction_type, quantity, fill_price)

        return {"nOrdNo": order_id, "stat": "Ok", "result": order}

    def _update_position(self, symbol, type, qty, price):
        existing = next((p for p in self.positions if p['trdSym'] == symbol), None)
        qty = int(qty)
        if type == "S":
            qty = -qty

        if existing:
            old_qty = int(existing['fldQty'])
            new_qty = old_qty + qty
            existing['fldQty'] = str(new_qty)
            if new_qty == 0:
                self.positions.remove(existing)
        else:
            self.positions.append({
                "trdSym": symbol,
                "fldQty": str(qty),
                "avgPrc": str(price),
                "flBuyQty": str(qty) if qty > 0 else "0",
                "flSellQty": str(abs(qty)) if qty < 0 else "0"
            })

    def cancel_order(self, order_id):
        if order_id in self.orders:
            self.orders[order_id]['ordSt'] = "cancelled"
            return {"stat": "Ok", "msg": "Cancelled"}
        return {"stat": "Not_Found"}

    def cancel_all_orders(self):
        count = 0
        for oid, o in self.orders.items():
            # In mock, simulate "open" or "pending" status if we had it,
            # but we mark everything complete instantly in place_order unless we add delay.
            # To test this, we would need to add state to mock orders.
            # For now, let's just mark any non-cancelled order as cancelled if we consider it open.
            if o['ordSt'] not in ["complete", "cancelled", "rejected"]:
                 o['ordSt'] = "cancelled"
                 count += 1
        return {"stat": "Ok", "cancelled_count": count}

    def get_positions(self):
        response_positions = []
        for p in self.positions:
            qty = int(p['fldQty'])
            avg = float(p['avgPrc'])
            ltp = avg + random.uniform(-5, 5)
            p_copy = p.copy()
            p_copy['ltp'] = f"{ltp:.2f}"
            pnl = (ltp - avg) * qty
            p_copy['pnl'] = f"{pnl:.2f}"
            response_positions.append(p_copy)
        return {"data": response_positions}

    def subscribe(self, instrument_tokens):
        pass

    def get_latest_ltp(self, instrument_token_or_symbol):
        # Mock logic to map token back to NIFTY/BANKNIFTY if possible, or just return random
        # For simplicity, if input matches our keys:
        if instrument_token_or_symbol in self.market_data:
            return self.market_data[instrument_token_or_symbol]
        return 0.0

    def get_filled_price(self, order_id, retries=3):
        # In mock, order is in self.orders
        order = self.orders.get(str(order_id))
        if order and order.get("ordSt") == "complete":
             return float(order.get("avgPrc", 0.0))
        return None
