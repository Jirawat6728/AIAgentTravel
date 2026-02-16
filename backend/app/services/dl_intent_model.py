"""
Optional Deep Learning (PyTorch LSTM) intent classifier for workflow keyword decoding.
ใช้เมื่อติดตั้ง torch แล้ว — LSTM รับข้อความ (word-level) แล้วจำแนก intent.
Fallback: ใช้ MLP (sklearn) หรือ LR ใน ml_keyword_service เมื่อไม่มี torch
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger

logger = get_logger(__name__)

_torch_available = False
try:
    import torch
    import torch.nn as nn
    _torch_available = True
except ImportError:
    pass

# Singleton LSTM model (trained on first use)
_dl_lstm_model: Optional[Any] = None
_dl_lstm_trained = False

# Define PyTorch classes only when torch is available (avoid NameError when torch not installed)
if _torch_available:
    import torch as _torch
    import torch.nn as _nn

    class _LSTMIntentNet(_nn.Module):
        """LSTM text classifier: Embedding -> LSTM -> Linear -> num_classes."""

        def __init__(
            self,
            vocab_size: int,
            num_classes: int,
            embed_dim: int = 64,
            hidden_dim: int = 128,
            num_layers: int = 1,
            dropout: float = 0.2,
        ):
            super().__init__()
            self.embed = _nn.Embedding(vocab_size, embed_dim, padding_idx=0)
            self.lstm = _nn.LSTM(
                embed_dim,
                hidden_dim,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0,
            )
            self.fc = _nn.Linear(hidden_dim, num_classes)
            self.num_classes = num_classes

        def forward(self, x: Any) -> Any:
            emb = self.embed(x)
            out, (h_n, _) = self.lstm(emb)
            last_hidden = h_n[-1]
            logits = self.fc(last_hidden)
            return logits


if _torch_available:
    class DLIntentModel:
        """
        Deep Learning LSTM intent classifier.
        Word-level vocab, LSTM, trained on (text, label) pairs.
        """

        def __init__(
            self,
            max_vocab_size: int = 2000,
            max_seq_len: int = 80,
            embed_dim: int = 64,
            hidden_dim: int = 128,
            num_layers: int = 1,
            epochs: int = 25,
            batch_size: int = 16,
        ):
            self.max_vocab_size = max_vocab_size
            self.max_seq_len = max_seq_len
            self.embed_dim = embed_dim
            self.hidden_dim = hidden_dim
            self.num_layers = num_layers
            self.epochs = epochs
            self.batch_size = batch_size
            self.vocab: Dict[str, int] = {"<pad>": 0, "<unk>": 1}
            self.label2idx: Dict[str, int] = {}
            self.idx2label: List[str] = []
            self.model: Optional[Any] = None
            self._device: Optional[Any] = None

        def _tokenize(self, text: str) -> List[str]:
            """Simple word-level tokenize (space + strip punctuation)."""
            text = (text or "").lower().strip()
            tokens = re.findall(r"[\w\u0e00-\u0e7f]+", text)
            return tokens[: self.max_seq_len]

        def _build_vocab(self, texts: List[str]) -> None:
            from collections import Counter
            counter: Counter[str] = Counter()
            for t in texts:
                counter.update(self._tokenize(t))
            for w, _ in counter.most_common(self.max_vocab_size - 2):
                if w not in self.vocab:
                    self.vocab[w] = len(self.vocab)
                    if len(self.vocab) >= self.max_vocab_size:
                        break

        def _text_to_ids(self, text: str) -> List[int]:
            tokens = self._tokenize(text)
            return [self.vocab.get(t, 1) for t in tokens]  # 1 = <unk>

        def _pad_ids(self, ids: List[int]) -> List[int]:
            if len(ids) >= self.max_seq_len:
                return ids[: self.max_seq_len]
            return ids + [0] * (self.max_seq_len - len(ids))

        def fit(self, X: List[str], y: List[str]) -> bool:
            """Train LSTM on (texts, labels). Returns True if trained successfully."""
            if not _torch_available:
                return False
            try:
                n = len(X)
                self._build_vocab(X)
                unique_labels = sorted(set(y))
                self.label2idx = {lbl: i for i, lbl in enumerate(unique_labels)}
                self.idx2label = unique_labels
                num_classes = len(unique_labels)
                self.model = _LSTMIntentNet(
                    vocab_size=len(self.vocab),
                    num_classes=num_classes,
                    embed_dim=self.embed_dim,
                    hidden_dim=self.hidden_dim,
                    num_layers=self.num_layers,
                )
                self._device = _torch.device("cuda" if _torch.cuda.is_available() else "cpu")
                self.model = self.model.to(self._device)
                optimizer = _torch.optim.Adam(self.model.parameters(), lr=1e-3)
                criterion = _nn.CrossEntropyLoss()
                self.model.train()
                n = len(X)
                for epoch in range(self.epochs):
                    perm = _torch.randperm(n).tolist()
                    total_loss = 0.0
                    for i in range(0, n, self.batch_size):
                        batch_idx = perm[i : i + self.batch_size]
                        batch_x = [self._pad_ids(self._text_to_ids(X[j])) for j in batch_idx]
                        batch_y = [self.label2idx[y[j]] for j in batch_idx]
                        x_t = _torch.tensor(batch_x, dtype=_torch.long, device=self._device)
                        y_t = _torch.tensor(batch_y, dtype=_torch.long, device=self._device)
                        optimizer.zero_grad()
                        logits = self.model(x_t)
                        loss = criterion(logits, y_t)
                        loss.backward()
                        optimizer.step()
                        total_loss += loss.item()
                    if (epoch + 1) % 5 == 0:
                        logger.debug("DL LSTM epoch %d loss=%.4f", epoch + 1, total_loss / max(1, n // self.batch_size))
                self.model.eval()
                logger.info(
                    "DL LSTM intent classifier trained on %d examples, vocab_size=%d, num_classes=%d",
                    len(X), len(self.vocab), num_classes,
                )
                return True
            except Exception as e:
                logger.warning("DL LSTM training failed: %s", e)
                return False

        def predict_proba(self, text: str) -> Optional[Tuple[str, List[float]]]:
            """Returns (predicted_label, list of class probabilities) or None on error."""
            if not _torch_available or self.model is None or not self.idx2label:
                return None
            try:
                with _torch.no_grad():
                    ids = self._pad_ids(self._text_to_ids(text))
                    x = _torch.tensor([ids], dtype=_torch.long, device=self._device)
                    logits = self.model(x)
                    probs = _torch.softmax(logits, dim=1).cpu().numpy()[0]
                    pred_idx = int(logits.argmax(dim=1).item())
                    pred_label = self.idx2label[pred_idx]
                    return (pred_label, probs.tolist())
            except Exception as e:
                logger.debug("DL LSTM predict_proba failed: %s", e)
                return None

        def predict(self, text: str) -> Optional[str]:
            out = self.predict_proba(text)
            return out[0] if out else None


def get_dl_intent_model() -> Optional[Any]:
    """Return singleton DL LSTM model (not trained yet). Call model.fit(X, y) from ml_keyword_service."""
    global _dl_lstm_model
    if not _torch_available:
        return None
    if _dl_lstm_model is None:
        _dl_lstm_model = DLIntentModel(
            max_vocab_size=2000,
            max_seq_len=80,
            embed_dim=64,
            hidden_dim=128,
            num_layers=1,
            epochs=25,
            batch_size=16,
        )
    return _dl_lstm_model


def is_dl_lstm_available() -> bool:
    return _torch_available
