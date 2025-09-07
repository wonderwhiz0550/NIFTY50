# nifty_agent.py
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import time
import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

class NiftyInvestmentAgent:
    def __init__(self):
        self.nifty_symbol = "^NSEI"
        self.vix_symbol = "^INDIAVIX"
        self.icici_nifty_etf = "ICICINIFTY.NS"  # ICICI Prudential Nifty ETF
        self.state_file = "investment_state.json"
        self.load_state()
        
        # Twilio configuration
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_phone = os.getenv('TWILIO_PHONE_NUMBER')
        self.user_phone = os.getenv('USER_PHONE_NUMBER')  # Indian mobile number
        
    def load_state(self):
        try:
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
        except FileNotFoundError:
            # Initialize state
            self.state = {
                "last_investment_date": None,
                "trading_days_since_last_investment": 0,
                "investment_history": []
            }
            self.save_state()
    
    def save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=4)
    
    def fetch_market_data(self):
        """Fetch current Nifty 50 and VIX data"""
        nifty = yf.Ticker(self.nifty_symbol)
        vix = yf.Ticker(self.vix_symbol)
        
        # Get historical data for SMA calculation
        nifty_hist = nifty.history(period="1mo")
        vix_data = vix.history(period="1d")
        
        # Calculate 20-day SMA
        sma_20 = nifty_hist['Close'].rolling(window=20).mean().iloc[-1]
        current_close = nifty_hist['Close'].iloc[-1]
        current_vix = vix_data['Close'].iloc[-1] if not vix_data.empty else None
        
        return {
            "nifty_close": current_close,
            "sma_20": sma_20,
            "vix": current_vix,
            "timestamp": datetime.now().isoformat()
        }
    
    def check_triggers(self, market_data):
        """Check if any investment triggers are met"""
        triggers = []
        
        # Trigger 1: Price Dip (≥2.5% below 20-Day SMA)
        price_dip_percentage = (market_data['nifty_close'] - market_data['sma_20']) / market_data['sma_20'] * 100
        if price_dip_percentage <= -2.5:
            triggers.append({
                "type": "PRICE_DIP",
                "message": f"Nifty 50 closed {abs(price_dip_percentage):.2f}% below 20-Day SMA"
            })
        
        # Trigger 2: Volatility Spike (VIX > 22)
        if market_data['vix'] and market_data['vix'] > 22:
            triggers.append({
                "type": "VOLATILITY_SPIKE",
                "message": f"India VIX closed at {market_data['vix']:.2f} (above 22)"
            })
        
        # Trigger 3: Time-Based Safety Net (21 trading days since last investment)
        if self.state['trading_days_since_last_investment'] >= 20:
            triggers.append({
                "type": "TIME_BASED",
                "message": f"20 trading days have passed since last investment"
            })
        
        return triggers
    
    def send_sms_alert(self, message):
        """Send SMS alert using Twilio"""
        if all([self.twilio_account_sid, self.twilio_auth_token, self.twilio_phone, self.user_phone]):
            try:
                client = Client(self.twilio_account_sid, self.twilio_auth_token)
                message = client.messages.create(
                    body=message,
                    from_=self.twilio_phone,
                    to=self.user_phone
                )
                print(f"SMS sent: {message.sid}")
            except Exception as e:
                print(f"Failed to send SMS: {e}")
        else:
            print("Twilio not configured. Message would be:", message)
    
    def execute_investment(self, trigger):
        """Execute investment based on trigger"""
        investment_date = datetime.now().date().isoformat()
        
        # Record investment
        self.state['last_investment_date'] = investment_date
        self.state['trading_days_since_last_investment'] = 0
        self.state['investment_history'].append({
            "date": investment_date,
            "trigger": trigger['type'],
            "message": trigger['message']
        })
        
        self.save_state()
        
        # Send confirmation
        alert_message = f"Investment triggered: {trigger['message']}. Executed 100% of month's allocation to ICICINIFTY."
        self.send_sms_alert(alert_message)
        
        return alert_message
    
    def daily_check(self):
        """Perform daily market check"""
        print(f"Checking market conditions at {datetime.now()}")
        
        # Update trading days counter
        if self.state['last_investment_date']:
            self.state['trading_days_since_last_investment'] += 1
        
        market_data = self.fetch_market_data()
        triggers = self.check_triggers(market_data)
        
        if triggers:
            # Execute investment for the first trigger found
            result = self.execute_investment(triggers[0])
            return {
                "action_taken": True,
                "message": result,
                "market_data": market_data,
                "trigger": triggers[0]
            }
        else:
            self.save_state()
            return {
                "action_taken": False,
                "message": "No triggers activated",
                "market_data": market_data,
                "triggers_checked": ["PRICE_DIP", "VOLATILITY_SPIKE", "TIME_BASED"]
            }

# For scheduled execution
def run_daily_check():
    agent = NiftyInvestmentAgent()
    return agent.daily_check()

if __name__ == "__main__":
    # For testing
    result = run_daily_check()
    print(result)