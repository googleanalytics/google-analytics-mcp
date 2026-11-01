# Copyright 2026 Google LLC All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Validation helpers for reporting request pagination."""


def validate_pagination(limit: int | None, offset: int | None) -> None:
    """Validate the shared pagination arguments used by reporting tools."""
    if limit is not None:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValueError("limit must be an integer between 1 and 250,000.")
        if not 1 <= limit <= 250_000:
            raise ValueError("limit must be an integer between 1 and 250,000.")

    if offset is not None:
        if isinstance(offset, bool) or not isinstance(offset, int):
            raise ValueError("offset must be a non-negative integer.")
        if offset < 0:
            raise ValueError("offset must be a non-negative integer.")
