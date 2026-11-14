import sys
import os
import socket
import urllib.request
import pytest

# Add project root to path so skills/agents are importable without install
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    """Unit tests may mock providers, but must never contact a broker or feed."""
    import requests
    import curl_cffi.requests

    def denied(*args, **kwargs):
        raise RuntimeError("External network disabled in unit tests; use a fixture")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(urllib.request, "urlopen", denied)
    monkeypatch.setattr(requests.sessions.Session, "request", denied)
    monkeypatch.setattr(curl_cffi.requests.Session, "request", denied)
