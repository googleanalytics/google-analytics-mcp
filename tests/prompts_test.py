# Copyright 2025 Google LLC All Rights Reserved.
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

"""Test cases for the prompts module."""

import unittest

from analytics_mcp import prompts as prompts_module
from mcp import types as mcp_types

_EXPECTED_PROMPT_NAMES = {
    "traffic-summary",
    "top-pages",
    "acquisition-overview",
    "compare-periods",
    "campaign-performance",
    "realtime-overview",
}


class TestListPrompts(unittest.TestCase):
    """Tests for list_prompts."""

    def test_returns_all_prompts(self):
        result = prompts_module.list_prompts()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), len(_EXPECTED_PROMPT_NAMES))

    def test_prompt_names(self):
        result = prompts_module.list_prompts()
        names = {p.name for p in result}
        self.assertEqual(names, _EXPECTED_PROMPT_NAMES)

    def test_all_prompts_have_description(self):
        for prompt in prompts_module.list_prompts():
            self.assertTrue(
                prompt.description,
                f"Prompt '{prompt.name}' is missing a description",
            )

    def test_required_arguments_are_marked(self):
        for prompt in prompts_module.list_prompts():
            for arg in prompt.arguments or []:
                if arg.name == "property_id":
                    self.assertTrue(
                        arg.required,
                        f"property_id in '{prompt.name}' should be required",
                    )


class TestGetPrompt(unittest.TestCase):
    """Tests for get_prompt."""

    def _get(self, name, **kwargs):
        return prompts_module.get_prompt(name, kwargs or None)

    def test_traffic_summary_basic(self):
        result = self._get("traffic-summary", property_id="12345")
        self.assertIsInstance(result, mcp_types.GetPromptResult)
        self.assertEqual(len(result.messages), 1)
        self.assertIn("12345", result.messages[0].content.text)
        self.assertIn("sessions", result.messages[0].content.text)

    def test_traffic_summary_default_date_range(self):
        result = self._get("traffic-summary", property_id="12345")
        self.assertIn("last 30 days", result.messages[0].content.text)

    def test_traffic_summary_custom_date_range(self):
        result = self._get(
            "traffic-summary",
            property_id="12345",
            date_range="last 7 days",
        )
        self.assertIn("last 7 days", result.messages[0].content.text)

    def test_top_pages_includes_limit(self):
        result = self._get("top-pages", property_id="12345", limit="5")
        self.assertIn("5", result.messages[0].content.text)

    def test_top_pages_default_limit(self):
        result = self._get("top-pages", property_id="12345")
        self.assertIn("10", result.messages[0].content.text)

    def test_acquisition_overview(self):
        result = self._get("acquisition-overview", property_id="12345")
        self.assertIn("sessionSourceMedium", result.messages[0].content.text)

    def test_compare_periods(self):
        result = self._get(
            "compare-periods",
            property_id="12345",
            current_period="last 7 days",
            previous_period="8-14 days ago",
        )
        text = result.messages[0].content.text
        self.assertIn("last 7 days", text)
        self.assertIn("8-14 days ago", text)

    def test_campaign_performance(self):
        result = self._get("campaign-performance", property_id="12345")
        self.assertIn(
            "sessionCampaignName", result.messages[0].content.text
        )

    def test_realtime_overview(self):
        result = self._get("realtime-overview", property_id="12345")
        self.assertIn(
            "run_realtime_report", result.messages[0].content.text
        )

    def test_all_messages_have_user_role(self):
        for name in _EXPECTED_PROMPT_NAMES:
            result = self._get(name, property_id="99999")
            for msg in result.messages:
                self.assertEqual(
                    msg.role,
                    "user",
                    f"Prompt '{name}' has non-user message role: {msg.role}",
                )

    def test_unknown_prompt_raises(self):
        with self.assertRaises(ValueError):
            prompts_module.get_prompt("not-a-real-prompt", {})

    def test_none_arguments_handled(self):
        result = prompts_module.get_prompt("traffic-summary", None)
        self.assertIsInstance(result, mcp_types.GetPromptResult)
