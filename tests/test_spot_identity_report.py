from spot import report
from spot import main as spot_main


def _meta():
    return {"when": "04.09 00:30", "n_cex": 1, "n_dex": 1,
            "n_pass": 2, "news_degraded": False}


def test_dex_report_shows_chain_full_contract_and_dex():
    contract = "So11111111111111111111111111111111111111112"
    c = {
        "layer": "DEX", "symbol": "FAKE", "mc": 5_000_000,
        "age_h": 72, "lifecycle": "FRESH", "breadth": 3, "median_p": 0.9,
        "network": "solana", "token": contract, "dex_id": "raydium",
        "pair_address": "PAIR123", "ident": {"project_name": "Fake Coin", "chain": "solana", "contract": contract},
        "flags": [], "f_volp": 2.0,
    }
    txt = report.build([c], _meta(), {"outcomes": {}})
    assert "Solana" in txt
    assert contract in txt
    assert "raydium DEX" in txt
    assert "AG/KONTRAT" in txt


def test_cex_report_shows_exchange_pair_and_single_contract():
    c = {
        "layer": "CEX", "symbol": "ABC", "mc": 100_000_000,
        "lifecycle": "CEX", "breadth": 2, "median_p": 0.8,
        "buy_venue": "gate", "buy_pair": "ABC/USDT",
        "platforms": {"ethereum": "0x1234567890abcdef"},
        "ident": {"project_name": "ABC Protocol"}, "flags": [], "f_volp": 1.5,
    }
    txt = report.build([c], _meta(), {"outcomes": {}})
    assert "NEREDEN: Gate | ABC/USDT" in txt
    assert "Ethereum | 0x1234567890abcdef" in txt


def test_multiple_cex_contracts_are_not_randomly_collapsed(monkeypatch):
    monkeypatch.setattr(spot_main.coingecko, "ticker_details", lambda coin_id: [
        {"market": "mexc", "base": "ABC", "target": "USDT", "trust_score": "green", "volume": 10},
        {"market": "gate", "base": "ABC", "target": "USDT", "trust_score": "green", "volume": 20},
    ])
    monkeypatch.setattr(spot_main.coingecko, "platforms", lambda coin_id: {
        "ethereum": "0xaaa", "base": "0xbbb"
    })
    c = {"coin_id": "abc", "ident": {}}
    spot_main.enrich_cex_identity(c)
    assert c["buy_venue"] == "gate"
    assert c["buy_pair"] == "ABC/USDT"
    assert c["network"] is None and c["token"] is None
    assert len(c["platforms"]) == 2


def test_dex_identity_uses_contract_not_name():
    a = {"network": "solana", "token": "ADDR_A"}
    b = {"network": "solana", "token": "ADDR_B"}
    assert f"{a['network']}:{a['token']}" != f"{b['network']}:{b['token']}"
