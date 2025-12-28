import tkinter as tk
from tkinter import ttk, messagebox
import json
import threading
import time
from datetime import datetime
from src.neo_client import NeoClientWrapper
from src.logic import get_atm_strike, calculate_stop_loss, calculate_target

class ScalperGUI:
    def __init__(self, root, config_path="config.json"):
        self.root = root
        self.root.title("Kotak Neo Scalper Pro")
        self.root.geometry("1000x700")

        # Load Config
        self.config_path = config_path
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        self.credentials = self.config.get("credentials", {})
        self.trade_settings = self.config.get("trading_settings", {})
        self.app_settings = self.config.get("app_settings", {})
        self.index_tokens = self.config.get("instrument_tokens", {})

        # Initialize Client
        self.client = NeoClientWrapper(self.config, use_mock=self.app_settings.get("use_mock_api", True))

        # State Variables
        self.selected_index = tk.StringVar(value="NIFTY")
        self.spot_price = tk.DoubleVar(value=0.0)
        self.atm_strike = tk.IntVar(value=0)

        # Calculate default expiry
        from src.logic import get_current_weekly_expiry
        default_expiry = get_current_weekly_expiry()
        self.expiry_str = tk.StringVar(value=default_expiry)

        self.is_running = True

        # Setup UI
        self._setup_login_ui()

    def _setup_login_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(expand=True)

        ttk.Label(frame, text="Scalper Login", font=("Helvetica", 16)).pack(pady=10)

        ttk.Button(frame, text="Login to Kotak Neo", command=self._perform_login).pack(pady=10)

    def _perform_login(self):
        if self.client.login():
            self._setup_dashboard_ui()
            self._start_data_feed()
        else:
            messagebox.showerror("Login Failed", "Check logs for details.")

    def _setup_dashboard_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        # --- Top Control Panel ---
        top_frame = ttk.Frame(self.root, padding="5")
        top_frame.pack(side=tk.TOP, fill=tk.X)

        # Instrument Tabs
        ttk.Label(top_frame, text="Instrument:").pack(side=tk.LEFT, padx=5)
        instruments = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
        for inst in instruments:
            rb = ttk.Radiobutton(top_frame, text=inst, variable=self.selected_index, value=inst, command=self._update_params)
            rb.pack(side=tk.LEFT, padx=5)

        # Expiry
        ttk.Label(top_frame, text="Expiry:").pack(side=tk.LEFT, padx=10)
        ttk.Entry(top_frame, textvariable=self.expiry_str, width=10).pack(side=tk.LEFT)

        # --- Settings Panel ---
        settings_frame = ttk.LabelFrame(self.root, text="Session Settings", padding="10")
        settings_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        # Quantity
        ttk.Label(settings_frame, text="Qty:").grid(row=0, column=0, padx=5)
        self.qty_var = tk.IntVar(value=self.trade_settings.get("default_quantity", 50))
        ttk.Entry(settings_frame, textvariable=self.qty_var, width=8).grid(row=0, column=1)

        # SL Points
        ttk.Label(settings_frame, text="SL (Pts):").grid(row=0, column=2, padx=5)
        self.sl_var = tk.IntVar(value=self.trade_settings.get("auto_sl_points", 10))
        ttk.Entry(settings_frame, textvariable=self.sl_var, width=8).grid(row=0, column=3)

        # Target Points
        ttk.Label(settings_frame, text="Tgt (Pts):").grid(row=0, column=4, padx=5)
        self.tgt_var = tk.IntVar(value=self.trade_settings.get("auto_target_points", 20))
        ttk.Entry(settings_frame, textvariable=self.tgt_var, width=8).grid(row=0, column=5)

        # Save Config Button
        ttk.Button(settings_frame, text="Save Defaults", command=self._save_config).grid(row=0, column=6, padx=20)

        # --- Market Data Section ---
        market_frame = ttk.Frame(self.root, padding="10")
        market_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(market_frame, text="Spot Price:", font=("Helvetica", 12)).pack(side=tk.LEFT, padx=10)
        self.lbl_spot = ttk.Label(market_frame, text="0.00", font=("Helvetica", 14, "bold"), foreground="blue")
        self.lbl_spot.pack(side=tk.LEFT, padx=10)

        ttk.Label(market_frame, text="ATM Strike:", font=("Helvetica", 12)).pack(side=tk.LEFT, padx=20)
        self.lbl_atm = ttk.Label(market_frame, text="0", font=("Helvetica", 14, "bold"), foreground="purple")
        self.lbl_atm.pack(side=tk.LEFT, padx=10)

        # --- Execution Buttons ---
        exec_frame = ttk.Frame(self.root, padding="20")
        exec_frame.pack(side=tk.TOP, fill=tk.X)
        exec_frame.columnconfigure(0, weight=1)
        exec_frame.columnconfigure(1, weight=1)

        # CALLS
        ce_frame = ttk.LabelFrame(exec_frame, text="CALL (CE)", padding="10")
        ce_frame.grid(row=0, column=0, sticky="ew", padx=10)

        self.btn_buy_ce = tk.Button(ce_frame, text="BUY CE", bg="green", fg="white", font=("Helvetica", 12, "bold"), height=2,
                                    command=lambda: self._place_order("CE", "B"))
        self.btn_buy_ce.pack(fill=tk.X, pady=5)

        self.btn_sell_ce = tk.Button(ce_frame, text="SELL CE", bg="red", fg="white", font=("Helvetica", 12, "bold"), height=2,
                                     command=lambda: self._place_order("CE", "S"))
        self.btn_sell_ce.pack(fill=tk.X, pady=5)

        # PUTS
        pe_frame = ttk.LabelFrame(exec_frame, text="PUT (PE)", padding="10")
        pe_frame.grid(row=0, column=1, sticky="ew", padx=10)

        self.btn_buy_pe = tk.Button(pe_frame, text="BUY PE", bg="green", fg="white", font=("Helvetica", 12, "bold"), height=2,
                                    command=lambda: self._place_order("PE", "B"))
        self.btn_buy_pe.pack(fill=tk.X, pady=5)

        self.btn_sell_pe = tk.Button(pe_frame, text="SELL PE", bg="red", fg="white", font=("Helvetica", 12, "bold"), height=2,
                                     command=lambda: self._place_order("PE", "S"))
        self.btn_sell_pe.pack(fill=tk.X, pady=5)

        # --- Positions Table ---
        pos_frame = ttk.LabelFrame(self.root, text="Positions", padding="5")
        pos_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("Symbol", "Qty", "Avg Price", "LTP", "P&L")
        self.tree = ttk.Treeview(pos_frame, columns=columns, show='headings', height=5)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor=tk.CENTER)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(pos_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Emergency Controls ---
        emergency_frame = ttk.Frame(self.root, padding="10")
        emergency_frame.pack(side=tk.BOTTOM, fill=tk.X)

        tk.Button(emergency_frame, text="PANIC: CLOSE ALL", bg="darkred", fg="white", font=("Helvetica", 12, "bold"),
                  command=self._panic_close).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        tk.Button(emergency_frame, text="REVERSE POSITION", bg="orange", fg="black", font=("Helvetica", 12, "bold"),
                  command=self._reverse_position).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    def _update_params(self):
        # Could trigger immediate re-subscription if strictly following active tab
        pass

    def _save_config(self):
        self.trade_settings["default_quantity"] = self.qty_var.get()
        self.trade_settings["auto_sl_points"] = self.sl_var.get()
        self.trade_settings["auto_target_points"] = self.tgt_var.get()

        self.config["trading_settings"] = self.trade_settings
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            messagebox.showinfo("Saved", "Settings saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def _place_order(self, opt_type, side):
        # 1. Get ATM Strike
        strike = self.atm_strike.get()
        if strike == 0:
            messagebox.showerror("Error", "ATM Strike not ready yet.")
            return

        # 2. Construct Symbol
        index = self.selected_index.get()
        expiry = self.expiry_str.get()
        symbol = f"{index}{expiry}{strike}{opt_type}"

        qty = self.qty_var.get()

        # Run in background thread to avoid freezing UI
        threading.Thread(target=self._place_order_task, args=(symbol, side, qty)).start()

    def _place_order_task(self, symbol, side, qty):
        try:
            # 3. Place Market Order
            print(f"Placing Order: {side} {symbol} x {qty}")
            resp = self.client.place_order(
                trading_symbol=symbol,
                transaction_type=side,
                quantity=str(qty),
                product="MIS",
                order_type="MKT"
            )

            if resp.get("stat", "") == "Ok" or "nOrdNo" in resp:
                 print(f"Order Success: {resp}")
                 # 4. Auto SL
                 if side == "B": # Requirement says "Once a BUY order is filled"
                     self._place_sl_order(symbol, qty, side, resp)
            else:
                print(f"Order Failed: {resp}")
                # Ideally update a status bar in UI safely
        except Exception as e:
            print(f"Order Thread Error: {e}")

    def _place_sl_order(self, symbol, qty, entry_side, entry_resp):
        try:
            sl_points = self.sl_var.get()
            if sl_points <= 0: return

            # Determine entry price
            # Mock returns 'result' dict with 'avgPrc'. Real API might differ.
            # Best is to fetch trade book, but for speed we estimate or use Last Price.
            # Here we assume we can get an approximate fill price.
            # In real high speed, we might use the LTP that triggered the decision or wait for order update.
            # We will use the current spot/LTP of that option as proxy or the avg price from response if available.

            # Mock Response Structure: {"result": {"avgPrc": ...}}
            avg_price = 0.0
            if "result" in entry_resp and "avgPrc" in entry_resp["result"]:
                avg_price = float(entry_resp["result"]["avgPrc"])
            else:
                # Real API flow: fetch trade price
                order_id = entry_resp.get("nOrdNo")
                if order_id:
                     print(f"Fetching filled price for {order_id}...")
                     fetched_price = self.client.get_filled_price(order_id)
                     if fetched_price:
                         avg_price = fetched_price
                         print(f"Fetched filled price: {avg_price}")
                     else:
                         print("Could not fetch filled price, retrying or checking LTP...")
                         pass # Could fall back to LTP logic here if critical

            if avg_price == 0:
                # Critical Fallback: Use current Spot/ATM as proxy?
                # No, better to alert or use safe assumption if needed.
                # For scalping, maybe use the estimated LTP if available?
                # We will log error for now as incorrect SL is dangerous.
                print("Error: Could not determine fill price for SL. SL NOT PLACED.")
                return

            trigger_price = calculate_stop_loss(avg_price, entry_side, sl_points)

            # SL Transaction Type is opposite
            sl_side = "S" if entry_side == "B" else "B"

            print(f"Placing SL: {sl_side} {symbol} @ {trigger_price}")

            # Kotak Neo SL-M usually: order_type="SL-M", trigger_price=X, price=0
            # Check NeoClientWrapper logic for mapping
            self.client.place_order(
                trading_symbol=symbol,
                transaction_type=sl_side,
                quantity=str(qty),
                product="MIS",
                order_type="SL-M",
                trigger_price=trigger_price,
                price=0 # Market SL
            )

        except Exception as e:
            print(f"Failed to place Auto SL: {e}")

    def _panic_close(self):
        # 1. Cancel all Pending Orders first (e.g. Stop Losses)
        print("Panic: Cancelling All Open Orders...")
        self.client.cancel_all_orders()

        # 2. Square off Positions
        positions_resp = self.client.get_positions()
        positions = positions_resp.get("data", [])

        if not positions:
            return

        for p in positions:
            qty = int(p.get("fldQty", 0))
            symbol = p.get("trdSym")

            if qty != 0:
                side = "S" if qty > 0 else "B"
                self.client.place_order(
                    trading_symbol=symbol,
                    transaction_type=side,
                    quantity=str(abs(qty)),
                    product="MIS",
                    order_type="MKT"
                )
        print("Panic Square Off Triggered")

    def _reverse_position(self):
        positions_resp = self.client.get_positions()
        positions = positions_resp.get("data", [])

        for p in positions:
            qty = int(p.get("fldQty", 0))
            symbol = p.get("trdSym")

            if qty != 0:
                side = "S" if qty > 0 else "B"
                reverse_qty = abs(qty) * 2

                self.client.place_order(
                    trading_symbol=symbol,
                    transaction_type=side,
                    quantity=str(reverse_qty),
                    product="MIS",
                    order_type="MKT"
                )
        print("Reverse Position Triggered")

    def _start_data_feed(self):
        # Subscribe to Indices
        # We subscribe to all 3 to be ready, or just the active one.
        tokens_to_sub = [
            {"instrument_token": v["token"], "exchange_segment": v["segment"]}
            for k, v in self.index_tokens.items()
        ]
        self.client.subscribe(tokens_to_sub)

        # Start loop
        self.feed_thread = threading.Thread(target=self._data_loop, daemon=True)
        self.feed_thread.start()

    def _data_loop(self):
        while self.is_running:
            try:
                # Prepare data to be updated on main thread
                ui_update_data = {}
                current_idx = self.selected_index.get()

                # 1. Get Spot Price
                price = 0.0
                if self.app_settings.get("use_mock_api"):
                    if hasattr(self.client.client, 'market_data'):
                         price = self.client.client.market_data.get(current_idx, 0.0)
                else:
                    # Real API: Get from local cache populated by WS
                    token_info = self.index_tokens.get(current_idx, {})
                    token = token_info.get("token")
                    price = self.client.get_latest_ltp(token)

                if price > 0:
                    ui_update_data["spot"] = price
                    ui_update_data["index"] = current_idx

                # 2. Get Positions
                positions_resp = self.client.get_positions()
                positions = positions_resp.get("data", [])

                # Schedule UI Update on Main Thread
                self.root.after(0, self._perform_ui_updates, ui_update_data, positions)

            except Exception as e:
                print(f"Data Loop Error: {e}")

            time.sleep(1)

    def _perform_ui_updates(self, data, positions):
        # Update Spot/ATM
        if "spot" in data:
            price = data["spot"]
            self.spot_price.set(round(price, 2))
            try:
                self.lbl_spot.config(text=f"{price:.2f}")

                current_idx = data.get("index", "NIFTY")
                step = 100 if "BANK" in current_idx or "SENSEX" in current_idx else 50
                atm = get_atm_strike(price, step)
                self.atm_strike.set(atm)
                self.lbl_atm.config(text=str(atm))
            except Exception:
                pass

        # Update Positions Table
        self._refresh_positions_table(positions)

    def _refresh_positions_table(self, positions):
        try:
            for item in self.tree.get_children():
                self.tree.delete(item)

            for p in positions:
                qty = p.get("fldQty", "0")
                if int(qty) == 0: continue

                sym = p.get("trdSym")
                avg = p.get("avgPrc", "0")
                ltp = p.get("ltp", "0")
                pnl = p.get("pnl", "0")

                tags = ("profit",) if float(pnl) >= 0 else ("loss",)

                self.tree.insert("", "end", values=(sym, qty, avg, ltp, pnl), tags=tags)

            self.tree.tag_configure("profit", foreground="green")
            self.tree.tag_configure("loss", foreground="red")
        except Exception:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = ScalperGUI(root)
    root.mainloop()
