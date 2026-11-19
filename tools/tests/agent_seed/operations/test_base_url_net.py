#  Unit tests for agent-seed base URL host/port helpers.

import tools.agent_seed.operations.base_url_net as agent_seed_base_url_net


def test_parse_host_port_defaults_http_port():
    assert agent_seed_base_url_net.parse_host_port("http://127.0.0.1") == ("127.0.0.1", 80)


def test_parse_host_port_explicit_port():
    assert agent_seed_base_url_net.parse_host_port("http://127.0.0.1:8000") == ("127.0.0.1", 8000)
