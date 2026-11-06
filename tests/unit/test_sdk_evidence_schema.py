# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_sdk_evidence_schema.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The evidence bundle schema kept in `contracts/` says what the closed schema of the shared SDK says.

The SDK is looked for in `HYDRA_UMC_SDK_DIR`, else next to this repository; without it the test is skipped, unless `HYDRA_UMC_REQUIRE_WORKSPACE=1` (the setting of CI),
which makes a missing SDK a failure.
"""
import json
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SDK = Path(os.environ["HYDRA_UMC_SDK_DIR"]) if os.environ.get("HYDRA_UMC_SDK_DIR") else ROOT.parent / "HYDRA-UMC-SDK"
SCHEMA = SDK / "contracts" / "json-schema" / "v1" / "evidence-bundle.schema.json"


def _shape(schema: dict) -> dict:
    return {"required": sorted(schema.get("required", [])), "closed": schema.get("additionalProperties") is False,
            "types": {name: (spec.get("type"), spec.get("minItems"), spec.get("minLength")) for name, spec in sorted(schema.get("properties", {}).items())}}


class SdkEvidenceSchemaTests(unittest.TestCase):
    def setUp(self):
        if not SCHEMA.is_file():
            if os.environ.get("HYDRA_UMC_REQUIRE_WORKSPACE") == "1":
                self.fail("the SDK is required (HYDRA_UMC_REQUIRE_WORKSPACE=1) but was not found")
            self.skipTest("the SDK is not available")

    def test_the_local_schema_has_the_shape_of_the_one_of_the_sdk(self):
        local = json.loads((ROOT / "contracts" / "evidence_bundle.schema.json").read_text(encoding="utf-8"))
        shared = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(_shape(local), _shape(shared))


if __name__ == "__main__":
    unittest.main()
