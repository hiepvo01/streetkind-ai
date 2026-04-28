"""
Static integrity tests that catch the class of bug that produced the
age_group / emergencyServicesCalled silent-binding regressions.

These run without any backend or frontend server, so they can live in
CI / pre-commit and fail fast on config drift.

Each test compares one of:
  - Pydantic schema field/sub-field names
  - JSON field-options config keys
  - Frontend tab `data.<field>` and `handleCheckboxChange('<section>'...)` references
  - Prompt template option lists
  - The frontend's `apiUrl()` helper usage

If any of these drift, the test fails with the exact diff so the offending
key is obvious.
"""

import json
import re
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]
FRONTEND_SRC = REPO / "frontend" / "src"
CONFIG_FIELDS = REPO / "config" / "fields"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    data.pop("_comment", None)
    return data


def _pydantic_field_names(model_cls) -> set[str]:
    return set(model_cls.model_fields.keys())


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Pydantic <-> config <-> frontend tab name alignment
# ---------------------------------------------------------------------------


class TestClientFormBinding:
    """For every nested-boolean / nested-int section on the Client form,
    verify the schema name, config key, frontend tab `data.<name>` reference,
    and `handleCheckboxChange('<name>')` argument all agree."""

    @pytest.fixture(scope="class")
    def client_schema_fields(self):
        from app.schemas.client_schema import ClientFormSchema
        return _pydantic_field_names(ClientFormSchema)

    @pytest.mark.parametrize("section_name,tab_file,uses_handler", [
        # (schema field, tab JS file, handler used)
        ("intoxicationSigns",     "ClientInfoTab.js",         "handleCheckboxChange"),
        ("drugUseSigns",          "ClientInfoTab.js",         "handleCheckboxChange"),
        ("offensiveConduct",      "ClientInfoTab.js",         "handleCheckboxChange"),
        ("selfHarmSigns",         "ClientInfoTab.js",         "handleCheckboxChange"),
        ("suicidalSigns",         "ClientInfoTab.js",         "handleCheckboxChange"),
        ("sexualAssault",         "ClientInfoTab.js",         "handleCheckboxChange"),
        ("physicalAssault",       "ClientInfoTab.js",         "handleCheckboxChange"),
        ("domesticViolence",      "ClientInfoTab.js",         "handleCheckboxChange"),
        ("reconnection",          "BasicSupportTab.js",       "handleCheckboxChange"),
        ("directions",            "BasicSupportTab.js",       "handleCheckboxChange"),
        ("transportInformation",  "BasicSupportTab.js",       "handleCheckboxChange"),
        ("escortedTo",            "BasicSupportTab.js",       "handleCheckboxChange"),
        ("safeSpace",             "BasicSupportTab.js",       "handleCheckboxChange"),
        ("basicAid",              "HealthSupportTab.js",      "handleCheckboxChange"),
        ("additionalAid",         "HealthSupportTab.js",      "handleCheckboxChange"),
        ("emergencyServicesCalled", "HealthSupportTab.js",    "handleCheckboxChange"),
        ("clientServiceReferrals", "ServicesReferredTab.js",  "handleCheckboxChange"),
        ("serviceInformation",    "ServicesReferredTab.js",   "handleCheckboxChange"),
        ("otherSupport",          "ServicesReferredTab.js",   "handleCheckboxChange"),
        ("injury",                "RiskMinimizationTab.js",   "handleCheckboxChange"),
    ])
    def test_section_name_consistency(self, client_schema_fields, section_name, tab_file, uses_handler):
        # 1. Backend schema must declare the field
        assert section_name in client_schema_fields, (
            f"ClientFormSchema is missing field {section_name!r}. "
            f"Either add it to the schema or remove from the test list."
        )

        # 2. The tab file must read `data.<section_name>` AND pass it to the
        #    handler with the same name. This is what catches the
        #    age_group / emergencyServicesCalled class of bug.
        tab_path = FRONTEND_SRC / "components" / "forms" / "ClientForm" / tab_file
        src = _read(tab_path)
        data_read_pattern = re.compile(rf"\bdata\.{re.escape(section_name)}\b")
        handler_pattern = re.compile(
            rf"{re.escape(uses_handler)}\(\s*['\"]{re.escape(section_name)}['\"]"
        )

        assert data_read_pattern.search(src), (
            f"{tab_file} does not read `data.{section_name}` - "
            f"the schema field is rendered as silently uneditable. "
            f"This is the same bug class as the age_group regression."
        )
        assert handler_pattern.search(src), (
            f"{tab_file} does not call `{uses_handler}('{section_name}', ...)`. "
            f"Even if the radio reads the right field, edits would write to "
            f"the wrong nested key."
        )


class TestClientFlatRadioBinding:
    """The integer-radio fields are flat (not nested). Verify they're read
    AND written by the matching schema name."""

    FLAT_RADIOS = [
        "physicalAssaultRisk",
        "sexualAssaultRisk",
        "clientConsciousness",
        "clientValuablesVisibility",
        "clientLostProperty",
    ]

    @pytest.fixture(scope="class")
    def schema_fields(self):
        from app.schemas.client_schema import ClientFormSchema
        return _pydantic_field_names(ClientFormSchema)

    @pytest.mark.parametrize("field", FLAT_RADIOS)
    def test_flat_radio(self, schema_fields, field):
        assert field in schema_fields, f"Schema missing {field}"
        src = _read(FRONTEND_SRC / "components" / "forms" / "ClientForm" / "RiskMinimizationTab.js")
        assert re.search(rf"\bdata\.{re.escape(field)}\b", src), (
            f"RiskMinimizationTab.js does not read `data.{field}` - radio shows unselected. "
            f"This is the bug pattern that hid `clientConsciousness` / `clientValuablesVisibility` / "
            f"`clientLostProperty` behind a phantom `data.theftRisk.*` namespace."
        )


# ---------------------------------------------------------------------------
# 2. Sub-key integrity for each nested section: schema model fields == JSON config keys
# ---------------------------------------------------------------------------


class TestSubKeyConsistency:
    """For every nested-boolean section, verify the JSON config keys exactly
    match the Pydantic sub-model fields. Drift here means the AI extracts
    a key the UI cannot render, OR the UI exposes a key the schema discards."""

    SECTIONS = [
        # (schema sub-class import path, json_file, json_key)
        ("client_schema.IntoxicationSigns",       "client.json", "intoxication_signs"),
        ("client_schema.ObservedVisibleDisclosed","client.json", "drug_use_signs"),
        ("client_schema.OffensiveConduct",        "client.json", "offensive_conduct"),
        ("client_schema.SelfHarmSigns",           "client.json", "self_harm_signs"),
        ("client_schema.SuicidalSigns",           "client.json", "suicidal_signs"),
        # ObservedVisibleDisclosed is reused for sexual/physical/domestic; one source
        ("client_schema.ObservedVisibleDisclosed","client.json", "assault_indicators"),
        ("client_schema.Reconnection",            "client.json", "reconnection"),
        ("client_schema.Directions",              "client.json", "directions"),
        ("client_schema.TransportInformation",    "client.json", "transport_information"),
        ("client_schema.EscortedTo",              "client.json", "escorted_to"),
        ("client_schema.BasicAid",                "client.json", "basic_aid"),
        ("client_schema.AdditionalAid",           "client.json", "additional_aid"),
        ("client_schema.EmergencyServicesCalled", "client.json", "emergency_services"),
        ("client_schema.ClientServiceReferrals",  "client.json", "service_referrals"),
        ("client_schema.OtherSupport",            "client.json", "other_support"),
    ]

    @pytest.mark.parametrize("schema_path,json_file,json_key", SECTIONS)
    def test_subkeys_match(self, schema_path, json_file, json_key):
        module_name, class_name = schema_path.split(".")
        mod = __import__(f"app.schemas.{module_name}", fromlist=[class_name])
        cls = getattr(mod, class_name)
        schema_keys = _pydantic_field_names(cls)

        config = _load_json(CONFIG_FIELDS / json_file)
        json_options = config.get(json_key, [])
        config_keys = {opt["key"] for opt in json_options}

        missing_in_config = schema_keys - config_keys
        extra_in_config = config_keys - schema_keys

        assert not (missing_in_config or extra_in_config), (
            f"\n{json_file}::{json_key} <-> {schema_path} drift:\n"
            f"  in schema but NOT in JSON config: {sorted(missing_in_config)}\n"
            f"  in JSON config but NOT in schema: {sorted(extra_in_config)}\n"
            f"This is the class of bug that made age_group radios show unselected for "
            f"every client."
        )


# ---------------------------------------------------------------------------
# 3. AI prompt rendering does not contradict the schemas it points at
# ---------------------------------------------------------------------------


class TestPromptSchemaConsistency:
    def test_safebase_prompt_age_group_keys_match_schema(self):
        """Whatever {age_group_keys} the safebase prompt advertises must be
        the GenderAgeCount schema field names. Drift here causes Pydantic
        to silently drop AI-extracted headcounts."""
        from app.config import get_safebase_prompt
        from app.schemas.safebase_schema import GenderAgeCount

        prompt = get_safebase_prompt()
        schema_keys = set(GenderAgeCount.model_fields.keys())

        # Find the rendered list of age group keys in the prompt by looking
        # for the canonical phrasing "age group ({...})".
        m = re.search(r"age group \(([^)]+)\)", prompt)
        assert m, f"safebase prompt no longer contains 'age group (...)' - update the test"
        listed_keys = {k.strip() for k in m.group(1).split(",")}

        assert listed_keys == schema_keys, (
            f"\nSafeBase prompt advertises age groups: {sorted(listed_keys)}\n"
            f"GenderAgeCount schema fields:           {sorted(schema_keys)}\n"
            f"Mismatched - the AI will produce keys that Pydantic drops."
        )

    def test_safebase_prompt_example_uses_schema_keys(self):
        """The 'map to male.from18to25 = 3' example in the prompt must use
        a key that's actually in the GenderAgeCount schema."""
        from app.config import get_safebase_prompt
        from app.schemas.safebase_schema import GenderAgeCount

        prompt = get_safebase_prompt()
        schema_keys = set(GenderAgeCount.model_fields.keys())

        # The hand-written example in the prompt mentions `male.<key>` directly.
        examples = re.findall(r"male\.(\w+)", prompt)
        for example_key in examples:
            assert example_key in schema_keys, (
                f"safebase prompt example uses `male.{example_key}` but that key "
                f"is not in GenderAgeCount: {sorted(schema_keys)}"
            )

    def test_incident_prompt_age_group_keys_match_client_schema(self):
        """Likewise for client age groups in the incident prompt example."""
        from app.config import get_incident_prompt

        prompt = get_incident_prompt()
        # The prompt names ageGroup keys inside parens or hyphenated lists.
        # We look at the comment that mentions ageGroup in the prompt body.
        m = re.search(r"ageGroup\s*\(([^)]+)\)", prompt)
        if not m:
            pytest.skip("incident prompt no longer hints ageGroup keys - test out of date")
        listed = {k.strip() for k in m.group(1).split("/")}
        # Client schema doc-comment says: lessThan18, 18to25, 26to39, over40
        expected = {"lessThan18", "18to25", "26to39", "over40"}
        assert listed == expected, (
            f"incident prompt ageGroup keys {sorted(listed)} != client schema "
            f"contract {sorted(expected)}"
        )


# ---------------------------------------------------------------------------
# 4. Every API call goes through apiUrl(); no raw '/api/...' path bypasses it
# ---------------------------------------------------------------------------


class TestApiUrlHelperUsage:
    def test_no_raw_api_paths_bypass_REACT_APP_API_BASE_URL(self):
        offenders = []
        for js in FRONTEND_SRC.rglob("*.js"):
            text = js.read_text(encoding="utf-8")
            for m in re.finditer(r"fetch\(\s*['\"`](/api/[^'\"`)]+)", text):
                # apiUrl() wraps via fetch(apiUrl(...)) - those don't match the regex above.
                offenders.append(f"{js.relative_to(REPO)}: fetch('{m.group(1)}', ...)")

        # Allow Dashboard's case which already wires apiUrl as a string
        # (it uses `${API_BASE_URL}/api/...` template literal so won't match anyway).
        assert not offenders, (
            "These fetch() calls bypass REACT_APP_API_BASE_URL and will 404 "
            "in cross-origin deployments:\n  " + "\n  ".join(offenders)
        )


# ---------------------------------------------------------------------------
# 5. Frontend initial form data shape matches the schema (no extra/missing top-level fields)
# ---------------------------------------------------------------------------


class TestInitialFormDataShape:
    def test_blank_client_keys_match_schema(self):
        """The blank client object must declare every Pydantic field on
        ClientFormSchema. Missing fields cause uncontrolled-input warnings
        and unexpected first-render state. Extra fields are silently dropped
        by Pydantic on submit and confuse round-trip equality checks.
        """
        from app.schemas.client_schema import ClientFormSchema

        text = _read(FRONTEND_SRC / "utils" / "initialFormData.js")
        m = re.search(r"createBlankClient\s*=\s*\(\)\s*=>\s*\(\{(.+?)\}\);", text, re.DOTALL)
        assert m, "Could not find createBlankClient object literal"
        body = m.group(1)

        # Extract DEPTH-0 keys only by tracking brace depth. Any property
        # whose key appears while we're inside a nested {} is a sub-field
        # and must not be counted as a top-level client field.
        client_keys: set[str] = set()
        depth = 0
        i = 0
        while i < len(body):
            ch = body[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            elif depth == 0:
                # At depth 0 only, look for `<identifier>:` as the start of a property
                m_key = re.match(r"\s*(\w+)\s*:", body[i:])
                if m_key:
                    client_keys.add(m_key.group(1))
                    i += m_key.end()
                    continue
            i += 1

        schema_keys = set(ClientFormSchema.model_fields.keys())
        missing = schema_keys - client_keys
        extra = client_keys - schema_keys

        assert not missing, (
            f"createBlankClient is missing schema fields: {sorted(missing)}\n"
            f"These will read as undefined on first render."
        )
        assert not extra, (
            f"createBlankClient has top-level fields NOT in ClientFormSchema: {sorted(extra)}\n"
            f"Pydantic drops these on submit - the user thinks data persists, it doesn't."
        )
