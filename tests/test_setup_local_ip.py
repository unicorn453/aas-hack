import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from setup_local_ip import pick_preferred_ip

def test_pick_preferred_ip_prefers_lan_over_docker_bridge():
    candidates = [
        "172.17.249.115",
        "172.18.0.1",
        "192.168.1.104",
        "127.0.0.1",
    ]

    assert pick_preferred_ip(candidates) == "192.168.1.104"


def test_pick_preferred_ip_ignores_loopback_and_link_local():
    candidates = [
        "127.0.0.1",
        "169.254.10.20",
        "10.1.24.64",
    ]

    assert pick_preferred_ip(candidates) == "10.1.24.64"
