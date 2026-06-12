import numpy as np
import pytest

torch = pytest.importorskip("torch", reason="torch not installed")

from skills.deep_regime_model import prepare_sequences, train_and_predict_regime


class TestPrepareSequences:
    def test_output_shapes(self):
        data = np.random.randn(50, 5).astype(np.float32)
        states = np.random.choice([0, 1, 2], size=50).astype(np.int64)
        X, Y = prepare_sequences(data, states, seq_len=10)
        assert X.shape == (40, 10, 5)   # 50 - 10 = 40 windows
        assert Y.shape == (40,)

    def test_target_is_next_step(self):
        data = np.ones((20, 3), dtype=np.float32)
        states = np.arange(20, dtype=np.int64)
        X, Y = prepare_sequences(data, states, seq_len=5)
        # First target should be states[5]
        assert Y[0] == 5

    def test_single_window(self):
        data = np.ones((11, 2), dtype=np.float32)
        states = np.zeros(11, dtype=np.int64)
        X, Y = prepare_sequences(data, states, seq_len=10)
        assert X.shape == (1, 10, 2)

    def test_dtypes(self):
        data = np.random.randn(20, 4).astype(np.float32)
        states = np.random.choice([0, 1, 2], size=20).astype(np.int64)
        X, Y = prepare_sequences(data, states, seq_len=5)
        assert X.dtype == np.float32
        assert Y.dtype == np.int64


class TestTrainAndPredictRegime:
    def _make_data(self, n=100, input_dim=5, seq_len=10):
        np.random.seed(0)
        inputs = np.random.randn(n, input_dim).astype(np.float32)
        states = np.random.choice([0, 1, 2], size=n).astype(np.int64)
        next_window = inputs[-seq_len:]
        return inputs, states, next_window

    def test_returns_three_probabilities(self):
        inputs, states, next_window = self._make_data()
        probs = train_and_predict_regime(inputs, states, next_window, seq_len=10, epochs=1)
        assert probs.shape == (3,)

    def test_probabilities_sum_to_one(self):
        inputs, states, next_window = self._make_data()
        probs = train_and_predict_regime(inputs, states, next_window, seq_len=10, epochs=1)
        assert np.sum(probs) == pytest.approx(1.0, abs=1e-5)

    def test_probabilities_non_negative(self):
        inputs, states, next_window = self._make_data()
        probs = train_and_predict_regime(inputs, states, next_window, seq_len=10, epochs=1)
        assert np.all(probs >= 0.0)

    def test_insufficient_data_returns_uniform_fallback(self):
        # Fewer than seq_len + 5 rows should trigger the fallback
        inputs = np.random.randn(12, 5).astype(np.float32)
        states = np.zeros(12, dtype=np.int64)
        next_window = inputs[-10:]
        probs = train_and_predict_regime(inputs, states, next_window, seq_len=10, epochs=1)
        expected = np.array([0.34, 0.33, 0.33], dtype=np.float32)
        np.testing.assert_array_equal(probs, expected)

    def test_different_input_dims(self):
        np.random.seed(1)
        n, input_dim, seq_len = 80, 3, 10
        inputs = np.random.randn(n, input_dim).astype(np.float32)
        states = np.random.choice([0, 1, 2], size=n).astype(np.int64)
        next_window = inputs[-seq_len:]
        probs = train_and_predict_regime(inputs, states, next_window, seq_len=seq_len, epochs=1)
        assert probs.shape == (3,)
        assert np.sum(probs) == pytest.approx(1.0, abs=1e-5)
