# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import nox
import os
import pathlib

PYTHON_VERSIONS = ["3.9", "3.10", "3.11", "3.12", "3.13"]

TEST_COMMAND = [
    "coverage",
    "run",
    "--append",
    "-m",
    "unittest",
    "discover",
    "--buffer",
    "-s=tests",
    "-p",
    "*_test.py",
]

FREEZE_COMMAND = ["python", "-m", "pip", "freeze"]
TEST_DEPENDENCIES = [
    "pyfakefs>=5.0.0,<6.0",
    "coverage==6.5.0",
]


@nox.session(venv_backend="none")
def format(session):
    """Runs the black formatter and applies formatting fixes."""
    session.run(
        "black",
        "-l",
        "80",
        "--exclude",
        r"/(v[0-9]+|\.eggs|\.git|_cache|\.nox|\.tox|\.venv|env|venv|\.svn|_build|buck-out|build|dist)/",
        ".",
    )


@nox.session(python=PYTHON_VERSIONS)
def tests(session):
    session.install(".")
    # modules for testing
    session.install(*TEST_DEPENDENCIES)
    session.run(*FREEZE_COMMAND)
    session.run(
        *TEST_COMMAND,
    )
