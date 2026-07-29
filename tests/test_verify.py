"""Tests for the action entry point.

An action whose logic lives in a `run:` block is untestable by construction,
which is how actions end up silently broken. This one is a script, so it gets a
suite: the exit codes, the GitHub output file, and the step summary are all
verified rather than assumed.
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import verify  # noqa: E402


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    from certkit import atom, make_spec
    from certkit.cert import CERT_SCHEMA

    domain = [atom({"payload": -1}), atom({"payload": 1}, -255)]
    sound_guard = [atom({"payload": 1, "record_len": -1}, 19)]
    safety = [atom({"payload": 1, "record_len": -1}, 3)]

    spec = make_spec(domain, sound_guard, safety, name="hb")
    (tmp_path / "hb.spec.json").write_text(json.dumps(spec))
    (tmp_path / "hb.cert.json").write_text(
        json.dumps(
            {
                "schema": CERT_SCHEMA,
                "spec_fingerprint": spec["fingerprint"],
                "obligations": [{"multipliers": {"2": 1, "3": 1}}],
            }
        )
    )

    # A forged certificate for the same spec.
    (tmp_path / "bad.spec.json").write_text(json.dumps(spec))
    (tmp_path / "bad.cert.json").write_text(
        json.dumps(
            {
                "schema": CERT_SCHEMA,
                "spec_fingerprint": spec["fingerprint"],
                "obligations": [{"multipliers": {"0": 1, "1": 1}}],
            }
        )
    )

    for key in list(os.environ):
        if key.startswith("INPUT_") or key in ("GITHUB_OUTPUT", "GITHUB_STEP_SUMMARY"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "out.txt"))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
    return tmp_path


def outputs(ws):
    text = (ws / "out.txt").read_text() if (ws / "out.txt").exists() else ""
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


def test_valid_certificate_passes(workspace, monkeypatch):
    monkeypatch.setenv("INPUT_SPEC", str(workspace / "hb.spec.json"))
    assert verify.run() == 0
    o = outputs(workspace)
    assert o["accepted"] == "1"
    assert o["refused"] == "0"


def test_forged_certificate_fails_the_job(workspace, monkeypatch):
    monkeypatch.setenv("INPUT_SPEC", str(workspace / "bad.spec.json"))
    assert verify.run() == 1
    assert outputs(workspace)["refused"] == "1"


def test_fail_on_refusal_false_reports_without_failing(workspace, monkeypatch):
    monkeypatch.setenv("INPUT_SPEC", str(workspace / "bad.spec.json"))
    monkeypatch.setenv("INPUT_FAIL_ON_REFUSAL", "false")
    assert verify.run() == 0
    assert outputs(workspace)["refused"] == "1"


def test_glob_matches_multiple_specs(workspace, monkeypatch):
    monkeypatch.setenv("INPUT_SPEC", str(workspace / "*.spec.json"))
    monkeypatch.setenv("INPUT_FAIL_ON_REFUSAL", "false")
    assert verify.run() == 0
    o = outputs(workspace)
    assert o["accepted"] == "1" and o["refused"] == "1"


def test_missing_spec_input_is_usage_error(workspace, monkeypatch):
    assert verify.run() == 2


def test_no_files_matched_is_usage_error(workspace, monkeypatch):
    monkeypatch.setenv("INPUT_SPEC", str(workspace / "nothing-*.json"))
    assert verify.run() == 2


def test_missing_certificate_is_reported(workspace, monkeypatch):
    (workspace / "hb.cert.json").unlink()
    monkeypatch.setenv("INPUT_SPEC", str(workspace / "hb.spec.json"))
    assert verify.run() == 2


def test_count_requires_a_box(workspace, monkeypatch):
    monkeypatch.setenv("INPUT_SPEC", str(workspace / "hb.spec.json"))
    monkeypatch.setenv("INPUT_COUNT", "true")
    assert verify.run() == 2


def test_counting_reports_over_acceptance(workspace, monkeypatch):
    monkeypatch.setenv("INPUT_SPEC", str(workspace / "hb.spec.json"))
    monkeypatch.setenv("INPUT_COUNT", "true")
    monkeypatch.setenv("INPUT_BOX", "payload=0:255,record_len=0:255")
    assert verify.run() == 0
    assert outputs(workspace)["over_acceptance"] == "0"


def test_step_summary_is_written(workspace, monkeypatch):
    monkeypatch.setenv("INPUT_SPEC", str(workspace / "hb.spec.json"))
    verify.run()
    text = (workspace / "summary.md").read_text()
    assert "## certkit" in text
    assert "ACCEPTED" in text


def test_summary_can_be_disabled(workspace, monkeypatch):
    monkeypatch.setenv("INPUT_SPEC", str(workspace / "hb.spec.json"))
    monkeypatch.setenv("INPUT_SUMMARY", "false")
    verify.run()
    assert not (workspace / "summary.md").exists()


def test_infer_cert_path():
    assert verify.infer_cert_path(Path("a/b.spec.json")).name == "b.cert.json"
    assert verify.infer_cert_path(Path("a/b.json")).name == "b.cert.json"


def test_parse_box():
    assert verify.parse_box("p=0:255,r=0:10") == {"p": (0, 255), "r": (0, 10)}


def test_env_flag():
    os.environ["X_FLAG"] = "TRUE"
    assert verify.env_flag("X_FLAG") is True
    os.environ["X_FLAG"] = "no"
    assert verify.env_flag("X_FLAG") is False
    del os.environ["X_FLAG"]
    assert verify.env_flag("X_FLAG", default=True) is True


# --------------------------------------------------------------------------- #
# SARIF output -- so a refusal reaches the Security tab, not just the job log
# --------------------------------------------------------------------------- #


def test_sarif_is_written_for_a_refusal(workspace, monkeypatch):
    out = workspace / "nested" / "certkit.sarif"
    monkeypatch.setenv("INPUT_SPEC", str(workspace / "bad.spec.json"))
    monkeypatch.setenv("INPUT_CERT", str(workspace / "bad.cert.json"))
    monkeypatch.setenv("INPUT_SARIF", str(out))
    assert verify.run() == 1

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["version"] == "2.1.0"
    run_ = doc["runs"][0]
    assert run_["tool"]["driver"]["name"] == "certkit"
    assert len(run_["results"]) == 1
    result = run_["results"][0]
    assert result["ruleId"] == "certkit/refused"
    assert result["level"] == "error"
    assert result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
    # Every ruleId used must be declared, or GitHub rejects the upload.
    declared = {r["id"] for r in run_["tool"]["driver"]["rules"]}
    assert {r["ruleId"] for r in run_["results"]} <= declared


def test_sarif_has_no_results_when_everything_is_accepted(workspace, monkeypatch):
    out = workspace / "certkit.sarif"
    monkeypatch.setenv("INPUT_SPEC", str(workspace / "hb.spec.json"))
    monkeypatch.setenv("INPUT_CERT", str(workspace / "hb.cert.json"))
    monkeypatch.setenv("INPUT_SARIF", str(out))
    assert verify.run() == 0
    assert json.loads(out.read_text(encoding="utf-8"))["runs"][0]["results"] == []


def test_no_sarif_written_when_the_input_is_empty(workspace, monkeypatch):
    monkeypatch.setenv("INPUT_SPEC", str(workspace / "hb.spec.json"))
    monkeypatch.setenv("INPUT_CERT", str(workspace / "hb.cert.json"))
    monkeypatch.setenv("INPUT_SARIF", "")
    assert verify.run() == 0
    assert list(workspace.glob("*.sarif")) == []


def test_unwritable_sarif_path_does_not_change_the_verdict(
    workspace, monkeypatch, capsys
):
    """Reporting must never override deciding."""
    (workspace / "a-file").write_text("not a directory", encoding="utf-8")
    monkeypatch.setenv("INPUT_SPEC", str(workspace / "hb.spec.json"))
    monkeypatch.setenv("INPUT_CERT", str(workspace / "hb.cert.json"))
    monkeypatch.setenv("INPUT_SARIF", str(workspace / "a-file" / "x" / "y.sarif"))
    assert verify.run() == 0  # still accepted
    assert "::warning::" in capsys.readouterr().out
