import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque

class QNetwork(nn.Module):
    def __init__(self, state_dim=4, action_dim=4):
        super().__init__()
        self.fc1 = nn.Linear(state_dim, 16)
        self.fc2 = nn.Linear(16, 16)
        self.out = nn.Linear(16, action_dim)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.out(x)

class ExecutionEnvironment:
    """
    Simulates order execution dynamics over multiple trading intervals.
    """
    def __init__(self, total_shares, bid_ask_spread, market_volume_15m, bondia_rate=0.11):
        self.total_shares = total_shares
        self.remaining_shares = total_shares
        self.spread = bid_ask_spread  # e.g., 0.005 (0.5%)
        self.market_volume = market_volume_15m
        self.bondia_rate = bondia_rate
        
        self.current_step = 0
        self.max_steps = 4  # 4 execution intervals in the day
        
        self.total_slippage = 0.0
        self.bondia_interest_earned = 0.0
        self.transaction_fees = 0.0

    def get_state(self):
        # State vector: [fractional_remaining, spread, market_volume_ratio, step_fraction]
        rem_fraction = self.remaining_shares / max(1.0, self.total_shares)
        vol_ratio = self.remaining_shares / max(1.0, self.market_volume)
        step_frac = self.current_step / self.max_steps
        return np.array([rem_fraction, self.spread, vol_ratio, step_frac], dtype=np.float32)

    def step(self, action):
        """
        Actions:
        0: Market Order (execute 100% of remaining shares immediately)
        1: Iceberg Limit Order (execute 25% of remaining, defer 75%)
        2: Defer (execute 0% now, accrue Bondia interest for this interval)
        3: Split Order (execute 50% limit order, defer 50% to next interval)
        """
        self.current_step += 1
        shares_to_execute = 0.0
        defer_fraction = 1.0
        
        if action == 0 or self.current_step >= self.max_steps:
            # Execute all remaining shares
            shares_to_execute = self.remaining_shares
            defer_fraction = 0.0
        elif action == 1:
            shares_to_execute = self.remaining_shares * 0.25
            defer_fraction = 0.75
        elif action == 2:
            shares_to_execute = 0.0
            defer_fraction = 1.0
        elif action == 3:
            shares_to_execute = self.remaining_shares * 0.5
            defer_fraction = 0.5

        # Calculate slippage based on trade size relative to market volume
        # Slippage increases quadratically with volume ratio (Kyle's Lambda impact)
        volume_ratio = shares_to_execute / max(1.0, self.market_volume)
        slippage_pct = (self.spread / 2.0) + 0.1 * (volume_ratio ** 2)
        step_slippage = shares_to_execute * slippage_pct
        self.total_slippage += step_slippage
        
        # Calculate standard 0.29% transaction fees on executed value
        step_fees = shares_to_execute * 0.0029
        self.transaction_fees += step_fees

        # Calculate Bondia cash sweeps interest on the capital deferred
        capital_deferred = self.remaining_shares * defer_fraction
        # Assume each step is 1/4 of a business day (which is 1/4 of 1/360 calendar year)
        interval_interest = capital_deferred * (self.bondia_rate / 360.0) * 0.25
        self.bondia_interest_earned += interval_interest

        # Update remaining shares
        self.remaining_shares -= shares_to_execute
        if self.remaining_shares < 0.01:
            self.remaining_shares = 0.0
            
        done = (self.remaining_shares == 0.0) or (self.current_step >= self.max_steps)
        
        # Reward is negative of costs (slippage + fees) + interest gained
        # We scale reward to be around similar magnitudes
        reward = -(step_slippage + step_fees) + self.bondia_interest_earned
        next_state = self.get_state()
        
        return next_state, reward, done

class DQNAgent:
    def __init__(self, state_dim=4, action_dim=4):
        self.q_net = QNetwork(state_dim, action_dim)
        self.target_net = QNetwork(state_dim, action_dim)
        self.target_net.load_state_dict(self.q_net.state_dict())
        
        self.optimizer = optim.Adam(self.q_net.parameters(), lr=0.01)
        self.memory = deque(maxlen=200)
        self.batch_size = 32
        self.gamma = 0.95
        
    def select_action(self, state, epsilon=0.1):
        if random.random() < epsilon:
            return random.randint(0, 3)
        state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            q_values = self.q_net(state_tensor)
        return int(torch.argmax(q_values).item())

    def train_step(self):
        if len(self.memory) < self.batch_size:
            return
        
        batch = random.sample(self.memory, self.batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        
        states = torch.tensor(np.array(states), dtype=torch.float32)
        actions = torch.tensor(actions, dtype=torch.int64).unsqueeze(1)
        rewards = torch.tensor(rewards, dtype=torch.float32)
        next_states = torch.tensor(np.array(next_states), dtype=torch.float32)
        dones = torch.tensor(dones, dtype=torch.float32)
        
        # Current Q-values
        curr_q = self.q_net(states).gather(1, actions).squeeze(1)
        
        # Target Q-values
        with torch.no_grad():
            next_q = self.target_net(next_states).max(1)[0]
            target_q = rewards + self.gamma * next_q * (1.0 - dones)
            
        loss = nn.MSELoss()(curr_q, target_q)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

# Global pre-trained execution agent to keep live routing fast
_GLOBAL_DQN_AGENT = None

def optimize_order_execution(shares_to_trade, bid_ask_spread, market_volume_15m, train_epochs=20):
    """
    Simulates RL DQN optimization for a rebalancing order execution.
    Returns:
        slippage_savings: float (MXN saved vs executing standard market order)
        interest_earned: float (Bondia sweeps interest captured during execution)
        fees: float (0.29% trading fees)
        execution_report: list of strings (step-by-step trace)
    """
    global _GLOBAL_DQN_AGENT
    if _GLOBAL_DQN_AGENT is None:
        _GLOBAL_DQN_AGENT = DQNAgent()
        
    # Baseline environment: standard instant market order (action = 0)
    baseline_env = ExecutionEnvironment(shares_to_trade, bid_ask_spread, market_volume_15m)
    baseline_env.step(action=0)
    baseline_slippage = baseline_env.total_slippage

    # Quick reinforcement training phase on this environment's parameters
    # This teaches the DQN agent to adapt to current market spread/volume conditions
    agent = _GLOBAL_DQN_AGENT
    for epoch in range(train_epochs):
        env = ExecutionEnvironment(shares_to_trade, bid_ask_spread, market_volume_15m)
        state = env.get_state()
        done = False
        while not done:
            action = agent.select_action(state, epsilon=0.3)
            next_state, reward, done = env.step(action)
            agent.memory.append((state, action, reward, next_state, done))
            state = next_state
        agent.train_step()
        if epoch % 5 == 0:
            agent.target_net.load_state_dict(agent.q_net.state_dict())

    # Evaluation phase (greedy execution routing)
    eval_env = ExecutionEnvironment(shares_to_trade, bid_ask_spread, market_volume_15m)
    state = eval_env.get_state()
    done = False
    trace = []
    
    while not done:
        action = agent.select_action(state, epsilon=0.0) # Greedy
        prev_shares = eval_env.remaining_shares
        state, reward, done = eval_env.step(action)
        executed = prev_shares - eval_env.remaining_shares
        
        action_names = ["Market Order", "Iceberg Limit (25%)", "Defer Sweeps", "Split Order (50%)"]
        trace.append(
            f"Step {eval_env.current_step}: Action = '{action_names[action]}' | "
            f"Traded {executed:.2f} shares | Remaining {eval_env.remaining_shares:.2f} shares"
        )

    # Slippage savings is baseline market order slippage minus DQN optimized slippage
    slippage_savings = max(0.0, baseline_slippage - eval_env.total_slippage)
    
    return {
        "slippage_savings": float(slippage_savings),
        "interest_earned": float(eval_env.bondia_interest_earned),
        "fees": float(eval_env.transaction_fees),
        "trace": trace
    }

if __name__ == "__main__":
    print("Testing DQN Reinforcement Learning Order Execution...")
    results = optimize_order_execution(shares_to_trade=1000.0, bid_ask_spread=0.008, market_volume_15m=3000.0)
    print("\nExecution Trace:")
    for line in results["trace"]:
        print(line)
    print(f"\nSlippage Savings: ${results['slippage_savings']:.2f} MXN")
    print(f"Bondia Interest Earned: ${results['interest_earned']:.4f} MXN")
    print(f"Transaction Fees Paid: ${results['fees']:.2f} MXN")
