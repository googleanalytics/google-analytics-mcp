"""Covers runbook tests 5-7 (phase-2-middleware.md 2.11).
Test 7 is the data-protection guarantee: an argument that is not on the
whitelist must not reach the row, whatever it is called."""

from analytics_mcp.usage_log.arguments import read_account_id


def test_reads_each_whitelisted_key():
    assert read_account_id({"customer_id": 123}) == "123"
    assert read_account_id({"merchant_id": "456"}) == "456"
    assert read_account_id({"property_id": 789}) == "789"


def test_returns_none_without_a_whitelisted_key():
    assert read_account_id({"page_size": 50}) is None
    assert read_account_id({}) is None
    assert read_account_id(None) is None


def test_ignores_every_other_argument():
    arguments = {
        "query": "SELECT campaign.name FROM campaign",
        "filter": "customer@example.com",
        "customer_id": 42,
    }
    assert read_account_id(arguments) == "42"
