import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="run slow tests",
    )
    parser.addoption(
        "--s3-requester-pays",
        action="store_true",
        default=False,
        help="run tests that require fetching data via s3 requester pays",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    config.addinivalue_line(
        "markers",
        "s3_requester_pays: mark test as requiring s3 requester pays to run",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
    if not config.getoption("--s3-requester-pays"):
        skip_s3_requestor_pays = pytest.mark.skip(
            reason="need --s3-requester-pays option to run",
        )
        for item in items:
            if "s3_requester_pays" in item.keywords:
                item.add_marker(skip_s3_requestor_pays)
