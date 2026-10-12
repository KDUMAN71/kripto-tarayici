from scanner import state as ST
from scanner.trade_accounting import SIGNAL_ONLY


def test_record_trade_is_not_realized_fill():
    st={"trades":[]}
    sig={"side":"LONG","entry_ref":100.0,"sl":99.0,"tp1":102.0,
         "tp1_hit":True,"target_touches":[{"type":"TARGET_TOUCH","target":"TP1","executed":False}]}
    ST._record_trade(st,"TESTUSDT",sig,"STOPPED",99.0)
    row=st["trades"][0]
    assert row["pnl_r"]==-1
    assert row["pnl_r_basis"]=="FULL_POSITION_PRICE_PATH_PROXY"
    assert row["execution_mode"]==SIGNAL_ONLY
    assert row["realized_r"] is None
    assert row["verified_exchange_fills"] is False
    assert row["target_touches"][0]["executed"] is False
