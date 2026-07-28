#!/usr/bin/env python3
"""Action entry point: verify certificates and report to GitHub.

Kept as a separate script rather than inline YAML so it can be tested. An action
whose logic lives in a `run:` block is untestable by construction, which is how
actions end up broken for months.

Reads its configuration from ``INPUT_*`` environment variables (the convention
GitHub composite actions use) and writes results to ``GITHUB_OUTPUT`` and
``GITHUB_STEP_SUMMARY`` when those are present. Absent them it simply prints,
so the script is runnable locally.
"""

from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def infer_cert_path(spec: Path) -> Path:
    """`foo.spec.json` -> `foo.cert.json`; otherwise `foo.cert.json` alongside."""
    name = spec.name
    if name.endswith(".spec.json"):
        return spec.with_name(name[: -len(".spec.json")] + ".cert.json")
    return spec.with_suffix(".cert.json")


def parse_box(text: str) -> Dict[str, Tuple[int, int]]:
    box: Dict[str, Tuple[int, int]] = {}
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        name, rng = part.split("=", 1)
        lo, hi = rng.split(":", 1)
        box[name.strip()] = (int(lo), int(hi))
    return box


def write_output(key: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"{key}={value}\n")


def write_summary(markdown: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(markdown + "\n")


# SARIF emission lives in certkit itself (`certkit.report`), so the wording of a
# finding is identical whether it reaches you through this action, the CLI's
# `--format sarif`, or another consumer. Two copies would drift.
#
# The fallback exists because `certkit-ref` lets you pin an older certkit that
# predates that module. Pinning should not silently lose SARIF output.
try:  # certkit >= 0.3
    from certkit.report import sarif_document, sarif_result

    def _sarif_finding(rule_id: str, spec_path: Path, message: str) -> Dict[str, Any]:
        verdict = "UNVERIFIED" if rule_id.endswith("unverified") else "REFUSED"
        return sarif_result(verdict, spec_path.as_posix(), message)

except ImportError:  # pragma: no cover - exercised only against an older pin
    _FALLBACK_RULES = [
        {
            "id": "certkit/refused",
            "name": "CertificateRefused",
            "shortDescription": {"text": "A proof certificate did not check out"},
            "defaultConfiguration": {"level": "error"},
        },
        {
            "id": "certkit/unverified",
            "name": "CertificateUnverified",
            "shortDescription": {"text": "A certificate was not bound to its spec"},
            "defaultConfiguration": {"level": "error"},
        },
    ]

    def sarif_document(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "certkit",
                            "informationUri": "https://github.com/nickharris808/certkit",
                            "rules": _FALLBACK_RULES,
                        }
                    },
                    "results": results,
                }
            ],
        }

    def _sarif_finding(rule_id: str, spec_path: Path, message: str) -> Dict[str, Any]:
        return {
            "ruleId": rule_id,
            "level": "error",
            "message": {"text": message},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": spec_path.as_posix()},
                        "region": {"startLine": 1},
                    }
                }
            ],
        }


def run(argv: Optional[List[str]] = None) -> int:
    spec_glob = os.environ.get("INPUT_SPEC", "").strip()
    cert_arg = os.environ.get("INPUT_CERT", "").strip()
    do_count = env_flag("INPUT_COUNT")
    box_text = os.environ.get("INPUT_BOX", "").strip()
    fail_on_refusal = env_flag("INPUT_FAIL_ON_REFUSAL", True)
    want_summary = env_flag("INPUT_SUMMARY", True)
    sarif_path = os.environ.get("INPUT_SARIF", "").strip()

    if not spec_glob:
        print("::error::input 'spec' is required", file=sys.stderr)
        return 2

    try:
        from certkit import check_certificate
    except ImportError:
        print("::error::certkit is not installed", file=sys.stderr)
        return 2

    specs = sorted(Path(p) for p in glob.glob(spec_glob))
    if not specs:
        print(f"::error::no files matched spec pattern {spec_glob!r}", file=sys.stderr)
        return 2

    if do_count and not box_text:
        print("::error::input 'box' is required when 'count' is true", file=sys.stderr)
        return 2

    sarif_results: List[Dict[str, Any]] = []
    accepted = refused = unverified = 0
    total_over = 0
    counted_any = False
    rows: List[str] = []
    exit_code = 0

    for spec_path in specs:
        cert_path = Path(cert_arg) if cert_arg else infer_cert_path(spec_path)

        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"::error file={spec_path}::cannot read spec: {exc}")
            rows.append(f"| `{spec_path}` | ERROR | unreadable spec |")
            refused += 1
            exit_code = 2
            continue

        try:
            cert = json.loads(cert_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"::error file={spec_path}::cannot read certificate {cert_path}: {exc}")
            rows.append(f"| `{spec_path}` | ERROR | missing certificate `{cert_path}` |")
            refused += 1
            exit_code = 2
            continue

        report = check_certificate(spec, cert)
        name = spec.get("name", spec_path.stem)

        # certkit 0.2+ reports three verdicts. UNVERIFIED means the arithmetic
        # checked out but a precondition was never established -- it is not an
        # acceptance, and calling it "REFUSED" would misdescribe it.
        verdict = getattr(report, "verdict", "ACCEPTED" if report.ok else "REFUSED")

        if report.ok:
            accepted += 1
            detail = f"{len(report.obligations)} obligation(s) discharged"
            print(f"certkit: ACCEPTED {name}")
            rows.append(f"| `{name}` | ACCEPTED | {detail} |")
        else:
            refused += 1
            reasons = "; ".join(
                o["reason"] for o in report.obligations if o["reason"]
            ) or report.reason
            print(f"::error file={spec_path}::certkit {verdict} {name}: {reasons}")
            rows.append(f"| `{name}` | **{verdict}** | {reasons} |")
            if verdict == "UNVERIFIED":
                unverified += 1
            sarif_results.append(
                _sarif_finding(
                    "certkit/unverified" if verdict == "UNVERIFIED" else "certkit/refused",
                    spec_path,
                    f"{verdict}: {name} -- {reasons}",
                )
            )
            if fail_on_refusal:
                exit_code = 1

        if do_count:
            try:
                from certkit import atom_from_json
                from exploit_counter import over_acceptance

                box = parse_box(box_text)
                result = over_acceptance(
                    [atom_from_json(a) for a in spec.get("domain", [])],
                    [atom_from_json(a) for a in spec.get("guard", [])],
                    [atom_from_json(a) for a in spec.get("safety", [])],
                    box,
                )
                if result.exact is not None:
                    counted_any = True
                    total_over += result.exact
                    rows.append(
                        f"| `{name}` | count | {result.exact} state(s) of {result.domain_volume} |"
                    )
                    print(f"certkit: {name} over-acceptance = {result.exact}")
                else:
                    rows.append(f"| `{name}` | count | declined (box too large) |")
            except Exception as exc:  # counting is advisory; never mask the verdict
                rows.append(f"| `{name}` | count | unavailable: {exc} |")

    write_output("accepted", str(accepted))
    write_output("refused", str(refused))
    write_output("over_acceptance", str(total_over) if counted_any else "")

    if sarif_path:
        try:
            Path(sarif_path).parent.mkdir(parents=True, exist_ok=True)
            Path(sarif_path).write_text(
                json.dumps(sarif_document(sarif_results), indent=2), encoding="utf-8"
            )
            print(f"certkit: wrote {len(sarif_results)} finding(s) to {sarif_path}")
        except OSError as exc:
            # Reporting is not the verdict. A SARIF write failure must not turn a
            # refusal into a pass, nor an acceptance into a failure.
            print(f"::warning::could not write SARIF to {sarif_path}: {exc}")

    tail = f", {unverified} of them unverified" if unverified else ""

    if want_summary:
        head = (
            "## certkit\n\n"
            f"**{accepted} accepted, {refused} refused{tail}**\n\n"
            "| item | result | detail |\n|---|---|---|\n"
        )
        write_summary(head + "\n".join(rows))

    print(f"certkit: {accepted} accepted, {refused} refused{tail}")
    if refused and not fail_on_refusal:
        print("certkit: fail-on-refusal is false; not failing the job")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(run())
