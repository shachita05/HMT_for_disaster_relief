from app.services.pipeline_service import _news_query


def test_uses_disaster_type_and_place_when_both_present():
    result = {"disaster_type": "Flood", "location": {"city": "Bengaluru"}}
    assert _news_query(result, "raw text") == "Flood Bengaluru"


def test_falls_back_to_disaster_type_only():
    result = {"disaster_type": "Flood", "location": {}}
    assert _news_query(result, "raw text") == "Flood"


def test_falls_back_to_place_only():
    result = {"disaster_type": "None", "location": {"state": "Karnataka"}}
    assert _news_query(result, "raw text") == "Karnataka"


def test_falls_back_to_raw_text_when_nothing_extracted():
    result = {"disaster_type": "None", "location": {}}
    assert _news_query(result, "raw text") == "raw text"


def test_prefers_city_over_district_over_state():
    result = {"disaster_type": "Flood", "location": {"city": "Bengaluru", "district": "X", "state": "Karnataka"}}
    assert _news_query(result, "raw text") == "Flood Bengaluru"
