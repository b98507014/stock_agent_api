import gymnasium as gym
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Normal
import os
import random
from gymnasium import spaces

class PricePredictor(nn.Module):
    """Neural network to predict next price based on historical prices"""
    def __init__(self, input_size=5, hidden_size=64):
        super(PricePredictor, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        return self.fc(lstm_out[:, -1, :])

class StockTradingEnv(gym.Env):
    """
    Reinforcement Learning Environment for Stock Trading Simulation
    Uses historical data and neural network for price prediction
    """

    def __init__(self, stock_codes=None, initial_balance=1000000, max_steps=1000,
                 data_dir='stock_data', use_nn_predictor=True):
        super(StockTradingEnv, self).__init__()

        self.stock_codes = stock_codes or [
            '2330', '2454', '2317', '3008', '4938', '2881', '2882',
            '1101', '2002', '1301', '1326', '2603'
        ]  # Use available stocks

        self.initial_balance = initial_balance
        self.max_steps = max_steps
        self.data_dir = data_dir
        self.use_nn_predictor = use_nn_predictor

        # Load stock data
        self.stock_data = {}
        self.dates = None

        for code in self.stock_codes:
            file_path = os.path.join(data_dir, f'{code}.csv')
            if os.path.exists(file_path):
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                self.stock_data[code] = df
                if self.dates is None:
                    self.dates = df.index
                else:
                    self.dates = self.dates.intersection(df.index)

        if not self.stock_data:
            raise ValueError("No stock data found. Please run fetch_stock_history.py first.")

        # Align all data to common dates
        for code in self.stock_codes:
            if code in self.stock_data:
                self.stock_data[code] = self.stock_data[code].loc[self.dates]

        self.n_stocks = len(self.stock_codes)
        self.n_dates = len(self.dates)

        # Initialize neural network predictor if enabled
        if self.use_nn_predictor:
            self.price_predictor = PricePredictor()
            self.train_predictor()

        # Action space: for each stock, 0 (hold), 1 (buy), 2 (sell)
        self.action_space = spaces.MultiDiscrete([3] * self.n_stocks)

        # Observation space: current prices (OHLCV), holdings, balance, portfolio_value
        obs_dim = self.n_stocks * 5 + self.n_stocks + 2  # prices(OHLCV) + holdings + balance + portfolio_value
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32)

        # Transaction cost
        self.transaction_cost = 0.001  # 0.1%

        self.reset()

    def train_predictor(self):
        """Train the neural network price predictor"""
        print("Training price predictor...")

        # Check if model already exists
        model_path = os.path.join(self.data_dir, 'price_predictor.pth')
        if os.path.exists(model_path):
            print("Loading existing price predictor model...")
            self.price_predictor.load_state_dict(torch.load(model_path))
            print("Model loaded successfully")
            return

        # Prepare training data
        train_data = []
        for code in self.stock_codes:
            if code in self.stock_data:
                prices = self.stock_data[code]['Close'].values
                # Create sequences of 10 days to predict next day
                for i in range(10, len(prices)):
                    seq = prices[i-10:i]
                    target = prices[i]
                    train_data.append((seq, target))

        if not train_data:
            print("Not enough data for training predictor")
            return

        # Simple training
        optimizer = optim.Adam(self.price_predictor.parameters(), lr=0.001)
        criterion = nn.MSELoss()

        for epoch in range(10):  # Quick training
            random.shuffle(train_data)
            total_loss = 0

            for seq, target in train_data[:1000]:  # Limit for speed
                optimizer.zero_grad()
                input_tensor = torch.FloatTensor(seq).unsqueeze(0).unsqueeze(-1).repeat(1, 1, 5)  # Repeat for OHLCV
                pred = self.price_predictor(input_tensor)
                loss = criterion(pred.squeeze(), torch.FloatTensor([target]))
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            if epoch % 5 == 0:
                print(f"Epoch {epoch}, Loss: {total_loss/len(train_data[:1000]):.4f}")

        # Save the trained model
        torch.save(self.price_predictor.state_dict(), model_path)
        print(f"Price predictor training completed and saved to {model_path}")

    def reset(self, seed=None, options=None):
        """Reset the environment to initial state"""
        super().reset(seed=seed)

        self.current_step = 0
        self.balance = self.initial_balance
        self.holdings = np.zeros(self.n_stocks)  # Number of shares held
        self.portfolio_value = self.initial_balance

        # Get initial observation
        obs = self._get_observation()
        return obs, {}

    def _get_observation(self):
        """Get current observation"""
        current_prices = []
        for code in self.stock_codes:
            if code in self.stock_data:
                day_data = self.stock_data[code].iloc[self.current_step]
                current_prices.extend([day_data['Open'], day_data['High'],
                                     day_data['Low'], day_data['Close'], day_data['Volume']])
            else:
                current_prices.extend([0, 0, 0, 0, 0])

        obs = np.array(current_prices + list(self.holdings) + [self.balance, self.portfolio_value])
        return obs.astype(np.float32)

    def step(self, action):
        """Execute one step in the environment"""
        if self.current_step >= self.n_dates - 1:
            return self._get_observation(), 0, True, False, {}

        # Execute actions
        reward = 0
        for i, act in enumerate(action):
            if act == 0:  # Hold
                continue
            elif act == 1:  # Buy
                # Buy with 10% of current balance
                invest_amount = self.balance * 0.1
                if invest_amount > 0 and self.stock_codes[i] in self.stock_data:
                    current_price = self.stock_data[self.stock_codes[i]].iloc[self.current_step]['Close']
                    shares_to_buy = invest_amount / current_price
                    cost = shares_to_buy * current_price * (1 + self.transaction_cost)
                    if cost <= self.balance:
                        self.holdings[i] += shares_to_buy
                        self.balance -= cost
            elif act == 2:  # Sell
                if self.holdings[i] > 0 and self.stock_codes[i] in self.stock_data:
                    current_price = self.stock_data[self.stock_codes[i]].iloc[self.current_step]['Close']
                    revenue = self.holdings[i] * current_price * (1 - self.transaction_cost)
                    self.balance += revenue
                    self.holdings[i] = 0

        # Calculate portfolio value
        old_portfolio_value = self.portfolio_value
        self.portfolio_value = self.balance
        for i, code in enumerate(self.stock_codes):
            if code in self.stock_data:
                current_price = self.stock_data[code].iloc[self.current_step]['Close']
                self.portfolio_value += self.holdings[i] * current_price

        # Reward is portfolio value change
        reward = self.portfolio_value - old_portfolio_value

        # Move to next step
        self.current_step += 1

        # Check if episode is done
        done = self.current_step >= self.max_steps or self.current_step >= self.n_dates - 1

        obs = self._get_observation()
        return obs, reward, done, False, {}

    def render(self):
        """Render the current state"""
        print(f"Step: {self.current_step}")
        print(f"Balance: {self.balance:.2f}")
        print(f"Portfolio Value: {self.portfolio_value:.2f}")
        print(f"Holdings: {dict(zip(self.stock_codes, self.holdings))}")

# Test the environment
if __name__ == "__main__":
    env = StockTradingEnv()
    obs, _ = env.reset()
    print(f"Observation shape: {obs.shape}")
    print(f"Action space: {env.action_space}")

    # Test a few steps
    for _ in range(5):
        action = env.action_space.sample()
        obs, reward, done, _, _ = env.step(action)
        print(f"Reward: {reward:.2f}, Done: {done}")
        if done:
            break