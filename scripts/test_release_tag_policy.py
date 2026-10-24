#!/usr/bin/env python3
"""Tests for the release tag and package version contract."""

from __future__ import annotations

import unittest

from release_tag_policy import TAG_RE, release_version


class ReleaseTagPolicyTests(unittest.TestCase):
    def test_maps_timestamp_package_tag_to_existing_package_version(self) -> None:
        tag = "v2026101818.0.0+slskdn.352"
        self.assertTrue(TAG_RE.fullmatch(tag))
        self.assertEqual(release_version(tag), "2026101818-slskdn.352")

    def test_preserves_regular_semver_versions(self) -> None:
        for tag, version in (
            ("v3.72.5", "3.72.5"),
            ("v3.72.5-slskdn.44", "3.72.5-slskdn.44"),
            ("v3.72.5-rc.1", "3.72.5-rc.1"),
            ("v3.72.5+build.7", "3.72.5+build.7"),
        ):
            with self.subTest(tag=tag):
                self.assertEqual(release_version(tag), version)

    def test_rejects_non_semver_and_malformed_tags(self) -> None:
        for tag in (
            "v2026101818-slskdn.352",
            "v01.2.3",
            "v1.02.3",
            "v1.2.03",
            "v1.2.3-rc.01",
            "v1.2",
            "1.2.3",
        ):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                release_version(tag)


if __name__ == "__main__":
    unittest.main()
