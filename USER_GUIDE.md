# Kotak Neo Scalper Pro - User Guide

This is a high-speed scalping terminal designed for Kotak Neo users. It offers a single-screen dashboard with one-click execution, automatic ATM strike selection, and automated stop-loss placement.

## 1. Installation

### Prerequisites
- Python 3.8 or higher installed on Windows.
- An active Kotak Neo account.
- API Credentials (Consumer Key, Secret) from the Kotak Neo API dashboard.

### Setup
1. Clone or download this repository.
2. Open a terminal/command prompt in the project folder.
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 2. Configuration

Before running the application, you must configure your credentials in `config.json`.

1. Open `config.json` in a text editor (Notepad, VS Code, etc.).
2. **Credentials Section**: Fill in your details.
   ```json
   "credentials": {
       "consumer_key": "YOUR_CONSUMER_KEY",
       "consumer_secret": "YOUR_CONSUMER_SECRET",
       "mobile_number": "9876543210",
       "password": "YOUR_LOGIN_PASSWORD",
       "mpin": "1234",
       "totp_secret": "YOUR_TOTP_SECRET_KEY"
   }
   ```
   *Note: `totp_secret` is the key you used to set up Google Authenticator/Authy.*

3. **Trading Settings**: Set your default preferences.
   - `default_quantity`: The quantity to trade per click (e.g., 50 for 1 lot of Nifty).
   - `auto_sl_points`: Points below entry to place Stop Loss (e.g., 10).
   - `enable_auto_sl`: Set to `true` to enable auto-stoploss.

4. **App Settings (Mock vs Real)**:
   - `"use_mock_api": true` -> Runs in simulation mode with fake data.
   - `"use_mock_api": false` -> **Connects to LIVE Kotak Neo account.**

5. **Instrument Tokens**:
   - Ensure the tokens for NIFTY, BANKNIFTY, etc., are up to date. These can be found in the Scrip Master provided by Kotak Neo.
   ```json
   "instrument_tokens": {
       "NIFTY": {"token": "26000", "segment": "nse_cm"},
       ...
   }
   ```

## 3. Usage

### Starting the App
Run the following command:
```bash
python main.py
```

### Dashboard Overview
1. **Login**: Click "Login to Kotak Neo". The app will authenticate using your credentials and TOTP.
2. **Instrument Tabs**: Click **NIFTY**, **BANKNIFTY**, or **FINNIFTY** to switch contexts.
   - The **Spot Price** and **ATM Strike** will update automatically based on live data.
3. **Execution**:
   - **BUY CE / SELL CE**: Buys or Sells the Call Option for the current ATM Strike.
   - **BUY PE / SELL PE**: Buys or Sells the Put Option for the current ATM Strike.
   - *Note: Orders are Market (MKT) orders.*
4. **Positions**: The table shows your open positions and real-time P&L.
5. **Panic Button**:
   - **PANIC: CLOSE ALL**: Immediately **cancels all pending orders** (like Stop Losses) and **squares off** all open positions at Market price. Use this in emergencies.
6. **Reverse Position**:
   - Closes the current position and opens an opposite position with double the quantity (net reverse).

## 4. Troubleshooting
- **UI Freezing**: If the UI lags, check your internet connection. Heavy data traffic can sometimes slow down updates.
- **Login Failed**: Verify your `totp_secret` and `mpin` in `config.json`.
- **Wrong Strike**: Ensure the `expiry` field (e.g., "24APR") matches the current contract format used by Kotak.

**Disclaimer**: This software is for educational purposes. Use at your own risk. Always test in Mock mode before trading with real capital.
