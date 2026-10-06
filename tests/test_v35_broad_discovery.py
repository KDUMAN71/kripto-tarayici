from scanner import config as C


def test_discovery_liquidity_is_broader_than_execution_reference():
    assert C.DISCOVERY_MIN_QUOTE_VOLUME_24H < C.MIN_QUOTE_VOLUME_24H
    assert C.DISCOVERY_MIN_QUOTE_VOLUME_24H == 2_000_000
    assert C.MIN_QUOTE_VOLUME_24H == 8_000_000


def test_metis_like_quote_volume_is_discoverable_but_below_execution_reference():
    metis_like_qv = 3_000_000
    assert metis_like_qv >= C.DISCOVERY_MIN_QUOTE_VOLUME_24H
    assert metis_like_qv < C.MIN_QUOTE_VOLUME_24H
