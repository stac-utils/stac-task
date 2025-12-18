import json
import os
from pathlib import Path

import pytest

from my_stac_task.task import MyStacTask


# Helper function to get test data
def get_test_cases():
    test_cases = []
    fixtures_dir = Path(__file__).parent / "fixtures" / "payloads"

    # Walk through the directory and find all directories with an 'in.json' file
    for dirpath, dirnames, filenames in os.walk(fixtures_dir):
        if "in.json" in filenames:
            input_file = Path(dirpath) / "in.json"
            output_file = Path(dirpath) / "out.json"
            exception_file = Path(dirpath) / "exception.txt"

            if exception_file.exists():
                # If there's an exception.txt, mark this case as an expected exception
                test_cases.append((input_file, exception_file, True))
            elif output_file.exists():
                # Otherwise, match input and output files
                test_cases.append((input_file, output_file, False))

    return test_cases


# Parametrize the test with the dynamic test cases
@pytest.mark.parametrize(
    "input_file, expected_output_file, expect_exception", get_test_cases()
)
def test_task(
    input_file: Path, expected_output_file: Path, expect_exception: bool
) -> None:
    input_payload = json.loads(input_file.read_text())

    if expect_exception:
        # If we expect an exception, test that it raises an exception
        with open(expected_output_file, "r") as exception_file:
            expected_exception = exception_file.read().strip()
        with pytest.raises(Exception, match=expected_exception):
            MyStacTask.handler(payload=input_payload, upload=False)
    else:
        # If we expect a successful result, compare the actual and expected output
        expected_output = json.loads(expected_output_file.read_text())
        actual_output = MyStacTask.handler(payload=input_payload, upload=False)
        # assert json.dumps(expected_output, sort_keys=True) == json.dumps(actual_output, sort_keys=True), "JSON objects do not match"
        # print(expected_output)
        # print(actual_output)
        assert actual_output == expected_output
