import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

class LSTMTransformerClassifier(nn.Module):
    def __init__(self, input_dim=5, hidden_dim=16, num_heads=2, num_classes=3):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True)
        # We set batch_first=True to align with LSTM output shapes
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim, 
            nhead=num_heads, 
            dim_feedforward=hidden_dim * 2, 
            batch_first=True,
            dropout=0.1
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=1)
        self.fc = nn.Linear(hidden_dim, num_classes)
        self.softmax = nn.Softmax(dim=-1)

    def forward(self, x):
        # Input shape: [batch, seq_len, input_dim]
        out, _ = self.lstm(x)  # [batch, seq_len, hidden_dim]
        out = self.transformer(out)  # [batch, seq_len, hidden_dim]
        # Pool/select last sequence element to represent final step state
        out = out[:, -1, :]  # [batch, hidden_dim]
        logits = self.fc(out)  # [batch, num_classes]
        return self.softmax(logits)

def prepare_sequences(data_matrix, target_states, seq_len=10):
    """
    Slices a continuous matrix of inputs and a list of target states into 
    supervised learning window batches.
    """
    X, Y = [], []
    for i in range(len(data_matrix) - seq_len):
        window = data_matrix[i : i + seq_len]
        target = target_states[i + seq_len]
        X.append(window)
        Y.append(target)
    return np.array(X, dtype=np.float32), np.array(Y, dtype=np.int64)

def train_and_predict_regime(inputs, target_states, next_step_input, seq_len=10, epochs=5):
    """
    Trains a lightweight LSTM-Transformer on historical features to predict
    the probability distribution of the next step's regime.
    
    inputs: np.ndarray shape [num_days, input_dim] (e.g. Asset_Ret, Vol, SPY_Ret, USDMXN_Ret, etc.)
    target_states: np.ndarray shape [num_days] containing historical HMM state labels (0, 1, or 2)
    next_step_input: np.ndarray shape [seq_len, input_dim] representing the most recent window.
    """
    # Safeguard size
    if len(inputs) < seq_len + 5:
        # Fallback to equal probabilities if not enough data
        return np.array([0.34, 0.33, 0.33], dtype=np.float32)

    X_train, Y_train = prepare_sequences(inputs, target_states, seq_len)
    
    # Convert to torch tensors
    X_tensor = torch.tensor(X_train)
    Y_tensor = torch.tensor(Y_train)
    
    input_dim = inputs.shape[1]
    model = LSTMTransformerClassifier(input_dim=input_dim, hidden_dim=16, num_heads=2, num_classes=3)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.01)
    
    # Fast lightweight CPU training loop
    model.train()
    batch_size = 64
    num_samples = len(X_train)
    
    for epoch in range(epochs):
        permutation = torch.randperm(num_samples)
        for i in range(0, num_samples, batch_size):
            indices = permutation[i : i + batch_size]
            batch_x, batch_y = X_tensor[indices], Y_tensor[indices]
            
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
    # Predict next step
    model.eval()
    with torch.no_grad():
        test_window = torch.tensor(next_step_input, dtype=torch.float32).unsqueeze(0)  # Shape [1, seq_len, input_dim]
        pred_probs = model(test_window).squeeze(0).numpy()
        
    return pred_probs


def check_multi_timeframe_regime_confluence(daily_regime: int, intraday_regime: int) -> dict:
    """
    Evaluates confluence between macro daily regime and tactical intraday regime.
    
    Regime conventions:
        0: Bull Market
        1: Bear Market
        2: Sideways / High-Volatility Chop
        
    Returns structured action recommendation enforcing multi-timeframe agreement.
    """
    confluence = False
    action = "CHOP_NEUTRAL"
    confidence = 0.5
    
    if daily_regime == 0 and intraday_regime == 0:
        confluence = True
        action = "BULL_LONG"
        confidence = 0.95
    elif daily_regime == 1 and intraday_regime == 1:
        confluence = True
        action = "BEAR_SHORT"
        confidence = 0.95
    elif daily_regime == 0 and intraday_regime == 1:
        confluence = False
        action = "DIP_BUY"
        confidence = 0.65
    elif daily_regime == 1 and intraday_regime == 0:
        confluence = False
        action = "BEAR_RALLY"
        confidence = 0.60
    else:
        confluence = False
        action = "CHOP_NEUTRAL"
        confidence = 0.50
        
    return {
        "daily_regime": int(daily_regime),
        "intraday_regime": int(intraday_regime),
        "has_confluence": confluence,
        "action": action,
        "confidence": confidence
    }

if __name__ == "__main__":
    # Test harness
    print("Testing LSTM-Transformer HMM Transition Prediction...")
    # Generate 100 days of dummy inputs (5 features: returns, volume, spy, fx, state)
    np.random.seed(42)
    dummy_inputs = np.random.randn(100, 5).astype(np.float32)
    dummy_states = np.random.choice([0, 1, 2], size=100).astype(np.int64)
    
    # Predict next step transition probability
    next_window = dummy_inputs[-10:]  # Last 10 days
    probs = train_and_predict_regime(dummy_inputs, dummy_states, next_window, seq_len=10, epochs=3)
    print(f"Predicted Transition Probabilities: {probs}")
    print(f"Sum of probabilities: {np.sum(probs):.4f}")
