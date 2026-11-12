"""Read `docker compose ... config --format json` on stdin; no Docker access."""

import json
import sys
from math import isfinite

RESOURCE_CEILINGS = {
    "api": (0.5, 512, 128), "db": (0.5, 512, 128), "minio": (0.5, 768, 128),
    "buckets": (0.25, 256, 64), "tests": (0.75, 1024, 256),
    "core-tests": (0.75, 1024, 256),
}


def integer_limit(value):
    assert type(value) is int or (
        isinstance(value, str) and value.isascii() and value.isdecimal()
    ), "expected integer limit in normalized Compose JSON"
    return int(value)


def check_resource_limits(services):
    assert services.keys() == RESOURCE_CEILINGS.keys(), "unexpected/missing test service"
    for name, (cpu_max, memory_mib, pids_max) in RESOURCE_CEILINGS.items():
        service = services[name]
        cpu, memory, pids = (service.get(key) for key in ("cpus", "mem_limit", "pids_limit"))
        assert isinstance(cpu, (str, int, float)) and not isinstance(cpu, bool), name
        cpu = float(cpu)
        assert isfinite(cpu) and 0 < cpu <= cpu_max, f"CPU budget: {name}"
        memory, pids = integer_limit(memory), integer_limit(pids)
        assert 0 < memory <= memory_mib * 1024**2, f"RAM budget: {name}"
        assert 0 < pids <= pids_max, f"PID budget: {name}"
        assert integer_limit(service.get("memswap_limit")) == memory, name
        assert service.get("scale", 1) == 1, f"multiple instances: {name}"
        assert service.get("deploy", {}).get("replicas", 1) == 1, name


def main():
    config = json.load(sys.stdin)
    services = config["services"]
    check_resource_limits(services)
    for name, service in services.items():
        assert not service.get("ports"), f"published port: {name}"
        assert not service.get("privileged"), f"privileged: {name}"
        assert service.get("network_mode", "") in ("", "service:db")
        for volume in service.get("volumes", []):
            assert volume["type"] != "bind", f"host bind: {name}"
    for resource in ("networks", "volumes"):
        assert all(not value.get("external") for value in config.get(resource, {}).values())
    for name in ("api", "buckets", "tests", "core-tests"):
        assert services[name].get("build"), f"missing source build: {name}"
        assert not services[name].get("image"), f"reused application image: {name}"
    assert services["api"]["build"]["target"] == "runtime"
    assert services["tests"]["build"]["target"] == "test"
    print("F02 remote config: no host ports/binds/external resources; source builds PASS")
    print("Test ceilings: 3.25 CPUs, 4096 MiB RAM, 960 PIDs; no extra swap")


if __name__ == "__main__":
    main()
