import os
import pandas as pd
import json
import math
import numpy as np
from datetime import datetime, timedelta
from stable_baselines3 import PPO
from RL_simulator import StockTradingEnv
# from fetch_stock_history import fetch_multiple_stocks  # Remove import-time import

class PaperTradingSimulator:
    def __init__(self, initial_balance=30000, account_file='/data/paper_trading_account.json', start_fresh=False, use_nn_predictor=True):
        self.initial_balance = initial_balance
        self.account_file = account_file
        self.start_fresh = start_fresh
        self.use_nn_predictor = use_nn_predictor

        # Initialize environment to get stock codes without training predictor when used for API.
        temp_env = StockTradingEnv(use_nn_predictor=self.use_nn_predictor)
        self.stock_codes = temp_env.stock_codes

        if self.start_fresh:
            self.reset_account()
        else:
            self.load_account()

        # Load PPO model
        model_path = 'models/ppo_stock_model.zip'
        if os.path.exists(model_path):
            self.model = PPO.load(model_path)
            print(f"Loaded PPO model from {model_path}")
        else:
            raise FileNotFoundError(f"PPO model not found at {model_path}")

        # Initialize environment for suggestions (will be reinitialized if data updates)
        self.env = None

    def load_account(self):
        """Load account state from file"""
        if os.path.exists(self.account_file):
            with open(self.account_file, 'r') as f:
                account_data = json.load(f)
                self.balance = account_data.get('balance', self.initial_balance)
                self.holdings = account_data.get('holdings', {code: 0.0 for code in self.stock_codes})
                self.last_update = account_data.get('last_update', None)
                print(f"Loaded account: Balance={self.balance}, Holdings={self.holdings}")
        else:
            self.reset_account()

    def reset_account(self):
        """Reset account to initial state with no holdings"""
        self.balance = self.initial_balance
        self.holdings = {code: 0.0 for code in self.stock_codes}
        self.last_update = None
        print(f"Initialized fresh account with balance {self.balance} and no holdings")

    def save_account(self):
        """Save account state to file"""
        account_data = {
            'balance': self.balance,
            'holdings': self.holdings,
            'last_update': datetime.now().isoformat()
        }
        with open(self.account_file, 'w') as f:
            json.dump(account_data, f, indent=2)
        print(f"Account saved: Balance={self.balance}, Holdings={self.holdings}")

    def update_stock_data(self):
        """Update all stock data"""
        print("Updating stock data...")
        from fetch_stock_history import fetch_multiple_stocks
        try:
            fetch_multiple_stocks()
            print("Stock data updated successfully")
        except Exception as e:
            print(f"Failed to update stock data: {e}")
            print("Using existing data for simulation")
            # Continue with existing data

    def get_current_prices(self):
        """Get current prices from the latest data"""
        current_prices = {}
        for code in self.stock_codes:
            file_path = os.path.join('stock_data', f'{code}.csv')
            if os.path.exists(file_path):
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                if not df.empty:
                    current_prices[code] = df.iloc[-1]['Close']  # Latest close price
        return current_prices

    def calculate_portfolio_value(self, current_prices):
        """Calculate current portfolio value"""
        portfolio_value = self.balance
        for code, shares in self.holdings.items():
            if code in current_prices:
                portfolio_value += shares * current_prices[code]
        return portfolio_value

    def get_ai_suggestion(self):
        """Get AI trading suggestions for today"""
        print("Getting AI trading suggestions...")

        # Initialize environment if not already done
        if self.env is None:
            print("Initializing environment...")
            self.env = StockTradingEnv(use_nn_predictor=self.use_nn_predictor)

        # Ensure environment has latest data by reinitializing if needed
        try:
            # Try to access stock data to check if env is valid
            _ = self.env.stock_data
        except:
            # Reinitialize environment with current data
            print("Reinitializing environment with updated data...")
            self.env = StockTradingEnv(use_nn_predictor=self.use_nn_predictor)

        # Reset environment to get current observation
        obs, _ = self.env.reset()

        # Get AI prediction (changed to deterministic=False for randomness)
        action, _ = self.model.predict(obs, deterministic=False)

        current_prices = self.get_current_prices()
        suggestions = {}

        for i, act in enumerate(action):
            code = self.stock_codes[i]
            price = current_prices.get(code)
            if price is None:
                suggestions[code] = {
                    'action': 'HOLD',
                    'shares': 0.0,
                    'amount': 0.0,
                    'price': None,
                    'note': 'No price data'
                }
                continue

            if act == 0:
                suggestions[code] = {
                    'action': 'HOLD',
                    'shares': 0.0,
                    'amount': 0.0,
                    'price': price,
                    'note': 'Hold current position'
                }
            elif act == 1:
                invest_amount = self.balance * 0.2
                shares_to_buy = math.ceil(invest_amount / price)
                shares_to_buy = max(1, shares_to_buy)
                amount = shares_to_buy * price
                suggestions[code] = {
                    'action': 'BUY',
                    'shares': shares_to_buy,
                    'amount': round(amount, 2),
                    'price': price,
                    'note': f'Buy at least 1 share ({amount:.2f} TWD)'
                }
            elif act == 2:
                shares_to_sell = self.holdings.get(code, 0.0)
                revenue = shares_to_sell * price * (1 - 0.001)
                suggestions[code] = {
                    'action': 'SELL',
                    'shares': round(shares_to_sell, 4),
                    'amount': round(revenue, 2),
                    'price': price,
                    'note': f'Sell all holdings ({shares_to_sell:.4f} shares)'
                }

        # Ensure at least one stock is suggested to buy at least 1 share
        has_buy = any(detail['action'] == 'BUY' for detail in suggestions.values())
        if not has_buy:
            import random
            available_codes = [code for code in self.stock_codes if code in current_prices and suggestions[code]['price'] is not None]
            if available_codes:
                code = random.choice(available_codes)
                price = current_prices[code]
                shares_to_buy = 1
                amount = shares_to_buy * price
                suggestions[code] = {
                    'action': 'BUY',
                    'shares': round(shares_to_buy, 4),
                    'amount': round(amount, 2),
                    'price': price,
                    'note': f'Forced buy at least 1 share ({amount:.2f} TWD)'
                }

        return suggestions, current_prices

    def execute_paper_trade(self, suggestions, current_prices):
        """Execute paper trades based on suggestions"""
        print("Executing paper trades...")

        transaction_cost = 0.001  # 0.1%
        bought_list = []

        for code, detail in suggestions.items():
            action = detail['action']
            if code not in current_prices:
                continue

            current_price = current_prices[code]

            if action == 'BUY':
                shares_to_buy = detail['shares']
                cost = shares_to_buy * current_price * (1 + transaction_cost)
                if cost <= self.balance:
                    self.holdings[code] += shares_to_buy
                    self.balance -= cost
                    print(f"BUY: {shares_to_buy:.4f} shares of {code} at {current_price:.2f}, cost: {cost:.2f} TWD")
                    bought_list.append(f"{code}: {shares_to_buy:.4f} Stock, Cost {cost:.2f} TWD")
                else:
                    print(f"BUY skipped for {code}: insufficient balance")

            elif action == 'SELL':
                shares_to_sell = self.holdings.get(code, 0.0)
                if shares_to_sell > 0:
                    revenue = shares_to_sell * current_price * (1 - transaction_cost)
                    self.balance += revenue
                    self.holdings[code] = 0.0
                    print(f"SELL: {shares_to_sell:.4f} shares of {code} at {current_price:.2f}, revenue: {revenue:.2f} TWD")
                else:
                    print(f"SELL skipped for {code}: no holdings")

            elif action == 'HOLD':
                print(f"HOLD: {self.holdings.get(code, 0.0):.4f} shares of {code}")

        if bought_list:
            print("\nPurchase details:")
            for item in bought_list:
                print(item)

    def run_daily_simulation(self):
        """Run daily paper trading simulation"""
        print("=" * 50)
        print("AI Stock Suggestion - Paper Trading Simulation")
        print("=" * 50)

        # Update stock data first (with error handling)
        if update_data:
            self.update_stock_data()

        # Get current prices and portfolio value
        current_prices = self.get_current_prices()
        portfolio_value = self.calculate_portfolio_value(current_prices)

        print(f"Current Balance: {self.balance:.2f} TWD")
        print(f"Current Portfolio Value: {portfolio_value:.2f} TWD")
        print("Current Holdings:")
        for code, shares in self.holdings.items():
            if shares > 0:
                value = shares * current_prices.get(code, 0)
                print(f"  {code}: {shares:.2f} shares ({value:.2f} TWD)")

        # Get AI suggestions
        suggestions, _ = self.get_ai_suggestion()
        print("\nAI Suggestions:")
        for code, detail in suggestions.items():
            action = detail['action']
            shares = detail['shares']
            amount = detail['amount']
            price = detail['price']
            note = detail.get('note', '')
            if action == 'BUY':
                print(f"  {code}: BUY {shares} shares, amount {amount:.2f} TWD, price {price:.2f} ({note})")
            elif action == 'SELL':
                print(f"  {code}: SELL {shares} shares, expected revenue {amount:.2f} TWD, price {price:.2f} ({note})")
            else:
                print(f"  {code}: HOLD ({note})")

        # Execute trades
        self.execute_paper_trade(suggestions, current_prices)

        # Recalculate portfolio value after trades
        portfolio_value = self.calculate_portfolio_value(current_prices)
        print(f"\nAfter Trading - Balance: {self.balance:.2f} TWD")
        print(f"After Trading - Portfolio Value: {portfolio_value:.2f} TWD")

        # Save account state
        self.save_account()

        print("Daily simulation completed!")
        return portfolio_value


def _to_python_types(value):
    """Convert numpy/pandas types to Python native types for JSON serialization."""
    if isinstance(value, dict):
        return {k: _to_python_types(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [_to_python_types(v) for v in value]
    elif isinstance(value, np.integer):
        return int(value)
    elif isinstance(value, np.floating):
        return float(value)
    elif isinstance(value, np.ndarray):
        return value.tolist()
    elif isinstance(value, (pd.Series, pd.Index)):
        return value.tolist()
    elif isinstance(value, (float, int, str, bool, type(None))):
        return value
    else:
        return value


def format_trading_report(current_balance, current_portfolio_value, current_holdings, 
                         current_prices, suggestions, balance_after, portfolio_value_after):
    """Format trading suggestions into a readable text report for Telegram.
    
    Args:
        current_balance: Balance before trading
        current_portfolio_value: Portfolio value before trading
        current_holdings: Dict of holdings before trading
        current_prices: Dict of current prices
        suggestions: Dict of AI suggestions
        balance_after: Balance after executing trades
        portfolio_value_after: Portfolio value after trading
        
    Returns:
        String formatted report
    """
    report_lines = []
    report_lines.append("=" * 50)
    report_lines.append("AI Stock Suggestion - Paper Trading Simulation")
    report_lines.append("=" * 50)
    
    # Current status before trading
    report_lines.append(f"\nCurrent Balance: {current_balance:.2f} TWD")
    report_lines.append(f"Current Portfolio Value: {current_portfolio_value:.2f} TWD")
    report_lines.append("Current Holdings:")
    
    has_holdings = False
    for code, shares in current_holdings.items():
        if shares > 0:
            has_holdings = True
            value = shares * current_prices.get(code, 0)
            report_lines.append(f"  {code}: {shares:.2f} shares ({value:.2f} TWD)")
    
    if not has_holdings:
        report_lines.append("  (No holdings)")
    
    # AI Suggestions
    report_lines.append("\nAI Suggestions:")
    for code, detail in suggestions.items():
        action = detail['action']
        shares = detail['shares']
        amount = detail['amount']
        price = detail['price']
        note = detail.get('note', '')
        
        if action == 'BUY':
            report_lines.append(f"  {code}: BUY {shares} shares, amount {amount:.2f} TWD, price {price:.2f} ({note})")
        elif action == 'SELL':
            report_lines.append(f"  {code}: SELL {shares} shares, expected revenue {amount:.2f} TWD, price {price:.2f} ({note})")
        else:
            report_lines.append(f"  {code}: HOLD ({note})")
    
    # After trading status
    report_lines.append(f"\nAfter Trading - Balance: {balance_after:.2f} TWD")
    report_lines.append(f"After Trading - Portfolio Value: {portfolio_value_after:.2f} TWD")
    report_lines.append("\nDaily simulation completed!")
    report_lines.append("=" * 50)
    
    return "\n".join(report_lines)


def _normalize_suggestions(suggestions):
    """Normalize suggestions and convert all types to Python native types."""
    normalized = {}
    for code, detail in suggestions.items():
        normalized[code] = {
            'action': str(detail['action']),
            'shares': int(detail['shares']) if detail['action'] == 'BUY' else float(detail['shares']),
            'amount': float(detail['amount']),
            'price': float(detail['price']) if detail['price'] is not None else None,
            'note': str(detail.get('note', ''))
        }
    return _to_python_types(normalized)


def make_suggestion(ticker=None, cash=30000, mode='paper', execute=True):
    """Generate AI trading suggestions and optionally execute trades.
    
    Args:
        ticker: None, empty string, 'auto', 'AUTO', single string, or list of strings
        cash: Initial cash amount (default 30000)
        mode: Only 'paper' is supported
        execute: If True, execute trades and update account
    
    Returns:
        Dict with suggestions, prices, and account state
    """
    if isinstance(ticker, str) and ticker.strip().lower() in ("", "auto"):
        ticker = None
    if mode != 'paper':
        raise ValueError("Only 'paper' mode is supported")

    # Handle ticker normalization
    if ticker is None or ticker == '' or (isinstance(ticker, str) and ticker.upper() == 'AUTO'):
        tickers = None  # Select all stocks
    elif isinstance(ticker, str):
        tickers = [ticker]
    elif isinstance(ticker, list):
        tickers = ticker
    else:
        raise ValueError('ticker must be a string or list of strings')

    # Validate cash
    if cash is None:
        cash_value = 30000
    else:
        try:
            cash_value = float(cash)
        except (TypeError, ValueError):
            raise ValueError('cash must be a number')
    
    if cash_value < 0:
        raise ValueError('cash must be non-negative')
    
    # Initialize simulator with persistent account (not fresh)
    simulator = PaperTradingSimulator(initial_balance=cash_value, start_fresh=False, use_nn_predictor=False)
    
    # Always update stock data with efficient fetch (recent 3 months only)
    simulator.update_stock_data()
    
    suggestions, current_prices = simulator.get_ai_suggestion()

    # Filter by ticker if specified
    if tickers is not None:
        tickers = [str(code) for code in tickers]
        invalid = [code for code in tickers if code not in simulator.stock_codes]
        if invalid:
            raise ValueError(f'Unsupported ticker(s): {invalid}')
        suggestions = {code: detail for code, detail in suggestions.items() if code in tickers}

    # Store current state before executing trades
    balance_before = simulator.balance
    portfolio_value_before = simulator.calculate_portfolio_value(current_prices)
    holdings_before = dict(simulator.holdings)

    # Execute trades if requested
    if execute:
        simulator.execute_paper_trade(suggestions, current_prices)
        simulator.save_account()

    # Calculate portfolio value after trades
    portfolio_value = simulator.calculate_portfolio_value(current_prices)

    # Normalize suggestions
    normalized_suggestions = _normalize_suggestions(suggestions)
    normalized_prices = {code: float(price) for code, price in current_prices.items()}
    normalized_holdings = {code: float(shares) for code, shares in simulator.holdings.items()}

    # Generate trading report for Telegram
    trading_report = format_trading_report(
        current_balance=balance_before,
        current_portfolio_value=portfolio_value_before,
        current_holdings=holdings_before,
        current_prices=current_prices,
        suggestions=suggestions,
        balance_after=float(simulator.balance),
        portfolio_value_after=float(portfolio_value)
    )

    return {
        'mode': mode,
        'cash': float(cash_value),
        'executed': bool(execute),
        'balance_after': float(simulator.balance),
        'portfolio_value': float(portfolio_value),
        'holdings': _to_python_types(normalized_holdings),
        'suggestions': normalized_suggestions,
        'current_prices': normalized_prices,
        'telegram_text': trading_report
    }


# Main function
if __name__ == "__main__":
    simulator = PaperTradingSimulator(start_fresh=False)
    final_value = simulator.run_daily_simulation()
    print(f"\nFinal Portfolio Value: {final_value:.2f} TWD")