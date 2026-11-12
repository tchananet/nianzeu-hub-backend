from copy import deepcopy

import pytest

from tests.infra.check_remote_config import check_resource_limits


@pytest.fixture
def bounded_services():
    # Independent expected allocation, including worst-case simultaneous runners.
    budgets = {
        "api": (0.5, 512, 128), "db": (0.5, 512, 128), "minio": (0.5, 768, 128),
        "buckets": (0.25, 256, 64), "tests": (0.75, 1024, 256),
        "core-tests": (0.75, 1024, 256),
    }
    return {name: dict(cpus=cpu, mem_limit=ram * 1024**2,
                       memswap_limit=ram * 1024**2, pids_limit=pids)
            for name, (cpu, ram, pids) in budgets.items()}


def test_accepts_bounded_stack(bounded_services):
    check_resource_limits(bounded_services)


def test_accepts_compose_decimal_byte_strings(bounded_services):
    for service in bounded_services.values():
        for field in ("cpus", "mem_limit", "memswap_limit", "pids_limit"):
            service[field] = str(service[field])
    check_resource_limits(bounded_services)


@pytest.mark.parametrize("service", ["api", "db", "minio", "buckets", "tests", "core-tests"])
@pytest.mark.parametrize("field", ["cpus", "mem_limit", "pids_limit", "memswap_limit"])
def test_rejects_missing_limit_on_every_service(bounded_services, service, field):
    del bounded_services[service][field]
    with pytest.raises(AssertionError):
        check_resource_limits(bounded_services)


@pytest.mark.parametrize("field,value", [
    ("cpus", 0), ("cpus", -1), ("cpus", 0.51), ("cpus", "nan"), ("cpus", "inf"),
    ("cpus", True), ("mem_limit", 0), ("mem_limit", -1), ("mem_limit", 513 * 1024**2),
    ("pids_limit", 0), ("pids_limit", -1), ("pids_limit", 129), ("pids_limit", 1.5),
    ("mem_limit", "512m"), ("mem_limit", True), ("mem_limit", "1.5"),
    ("memswap_limit", -1), ("memswap_limit", 1024**3), ("scale", 2),
    ("deploy", {"replicas": 2}),
])
def test_rejects_unbounded_or_excessive_resources(bounded_services, field, value):
    bounded_services["api"][field] = value
    with pytest.raises(AssertionError):
        check_resource_limits(bounded_services)


def test_rejects_extra_or_missing_service(bounded_services):
    extra = deepcopy(bounded_services)
    extra["extra-runner"] = extra["tests"]
    with pytest.raises(AssertionError):
        check_resource_limits(extra)
    del bounded_services["core-tests"]
    with pytest.raises(AssertionError):
        check_resource_limits(bounded_services)
