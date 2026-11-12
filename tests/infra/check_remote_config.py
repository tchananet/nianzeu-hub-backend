"""Read `docker compose ... config --format json` on stdin; no Docker access."""

import json
import sys


def main():
    config = json.load(sys.stdin)
    services = config["services"]
    assert {"api", "db", "minio", "buckets", "tests", "core-tests"} <= services.keys()
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


if __name__ == "__main__":
    main()
