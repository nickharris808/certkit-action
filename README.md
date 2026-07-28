# certkit-action

[![self-test](https://github.com/nickharris808/certkit-action/actions/workflows/self-test.yml/badge.svg)](https://github.com/nickharris808/certkit-action/actions/workflows/self-test.yml)
[![status](https://img.shields.io/badge/status-pre--release-orange.svg)](#usage)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**Re-check proof certificates in CI. Fail the build when one does not check out.**

> **Try it now, no install:** [open the browser demo](https://huggingface.co/spaces/nickh007/certkit-demo) and press **Load a forgery** — the checker refuses it, client-side.

<a id="usage"></a>

## 30-second quickstart

Add one step to any workflow:

```yaml
- uses: nickharris808/certkit-action@main
  with:
    spec: certs/*.spec.json
```

That is the whole integration. Each spec's certificate is inferred by replacing `.spec.json` with
`.cert.json`, every certificate is independently re-checked, and the job fails if any is refused.

## What it looks like

The action writes a table to the job summary:

| item | result | detail |
|---|---|---|
| `heartbleed` | ACCEPTED | 1 obligation(s) discharged |
| `bounds-check` | **REFUSED** | non-strict combination needs const > 0, got -65535 |

and annotates the failing file inline, so a refusal shows up on the PR diff rather than buried in a
log.

## Inputs

| Input | Default | Meaning |
|---|---|---|
| `spec` | *required* | path or glob, e.g. `certs/*.spec.json` |
| `cert` | inferred | explicit certificate path; inferred from the spec name if omitted |
| `count` | `false` | also run `exploit-counter` and report exact over-acceptance |
| `box` | — | variable box for counting, e.g. `payload=0:255,record_len=0:255` |
| `fail-on-refusal` | `true` | set `false` to report without failing while adopting |
| `certkit-version` | latest | version specifier, e.g. `==0.1.0` — **pin this** |
| `summary` | `true` | write the table to the job summary |

## Outputs

| Output | Meaning |
|---|---|
| `accepted` | number of certificates accepted |
| `refused` | number refused |
| `over-acceptance` | total over-acceptance across counted specs, empty if counting was off |

## Counting how bad a refusal is

```yaml
- uses: nickharris808/certkit-action@main
  with:
    spec: certs/*.spec.json
    count: "true"
    box: "payload=0:255,record_len=0:255"
```

A refused certificate then reports not just *that* the guard is unsound but exactly how many states
it wrongly admits — which is the difference between "the check failed" and "this admits 509 states,
one every ~129 random draws".

## Adopting gradually

Set `fail-on-refusal: false` on first rollout. The action still annotates and summarises; it just
does not block. Flip it to `true` once the existing certificates are clean.

## Pin the version

```yaml
- uses: nickharris808/certkit-action@main
  with:
    spec: certs/*.spec.json
    certkit-version: "==0.1.0"
```

Leaving `certkit-version` unset installs the newest release, which means a checker upgrade can change
your build result without a commit. For a security gate that is usually the wrong trade.

## Why a script, not a `run:` block

The verification logic lives in `verify.py` rather than inline YAML, so it has a test suite — 14
tests covering exit codes, globbing, missing files, the counting path, and the GitHub output and
summary side effects. An action whose logic is embedded in YAML cannot be tested, which is how
actions end up broken for months without anyone noticing.

Run them locally:

```bash
pip install "certkit@git+https://github.com/nickharris808/certkit@main" "exploit-counter@git+https://github.com/nickharris808/exploit-counter@main" pytest
pytest tests
```

## Scope

The action re-checks certificates you already have. It does not produce them — `certkit` contains no
solver by design. See [`certkit`](https://github.com/nickharris808/certkit) for where certificates come from.

---

## The closed core

These packages are the *checking* half. They deliberately contain no proof search, which is what keeps
them small enough to audit — and it means something upstream has to produce certificates.

For obligations over full machine-word domains, enumeration does not scale and a decision procedure
that does not enumerate is required: solver-free elimination emitting replayable certificates. That
engine, the repair synthesiser that derives a minimal guard from a refutation, and the evolutionary
search that drives them are **not** in this repository and are available commercially.

The split is deliberate and permanent. **The checker is free and always will be** — a certificate you
cannot independently verify is worth nothing, so charging for verification would defeat the format.
What costs money is *producing* certificates at scale.

## The rest of the toolkit

| | |
|---|---|
| **[certkit](https://github.com/nickharris808/certkit)** | the certificate format and the independent checker |
| **[exploit-counter](https://github.com/nickharris808/exploit-counter)** | if a guard is unsound, exactly how many states escape |
| **[crs-mcp](https://github.com/nickharris808/crs-mcp)** | the verdict surface AI coding agents call, over MCP |
| **[soundnessbench](https://github.com/nickharris808/soundnessbench)** | the benchmark that grades all of the above |
| **[certkit-action](https://github.com/nickharris808/certkit-action)** | run the check in your CI |
| **[pytest-mutation-verified](https://github.com/nickharris808/pytest-mutation-verified)** | prove your regression test can actually fail |
| **[cve-proof-corpus](https://huggingface.co/datasets/nickh007/cve-proof-corpus)** | six real CVEs with machine-checkable proofs |
| **[Try it in your browser](https://huggingface.co/spaces/nickh007/certkit-demo)** | no install; watch a forgery get refused |

## License

Apache-2.0.
