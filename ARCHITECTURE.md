# Architecture

## What runs

A composite GitHub Action: install `certkit` from source, run the checker on a spec/certificate
pair, render the result, and set the job status. The interesting parts are the exit-code mapping and
the SARIF output, because those are what a reviewer actually sees.

## Files

| File | Role |
|---|---|
| `action.yml` | Inputs, the composite steps, and the pinned `certkit-ref`. |
| `verify.py` | Runs the check and renders. Delegates every format to `certkit.report`, so a refusal is worded identically here and in the CLI. |
| `tests/test_verify.py` | Exercises each verdict and each output path. |

## The exit-code mapping, which is the whole contract

| certkit exit | Verdict | Action result |
|---:|---|---|
| 0 | `ACCEPTED` | pass |
| 1 | `REFUSED` | **fail** |
| 2 | usage error | **fail** |
| 3 | `UNVERIFIED` | **fail** |

Exit 3 failing is the decision worth defending. It means the tool declined to certify — a
precondition of the check never happened. In a gate, "declined to certify" and "refused" have
exactly the same consequence, and an action that treated 3 as a warning would let a merge proceed on
a check that explicitly did not run.

## Why `certkit-ref` exists

The action used to tell users to pin `certkit-version: "==0.1.0"`, which 404s because the package is
not on PyPI. `certkit-ref` pins a git ref instead, defaulting to `main`. Pinning a ref is the
honest version of "pin your dependency" until publication happens.

## SARIF

A refusal becomes a code-scanning alert anchored at the spec file, under rule `certkit/refused`.
`UNVERIFIED` gets its own rule, `certkit/unverified`, rather than being folded into either the
refusal rule or silence — the Security tab is exactly the place where a third verdict would
otherwise get rounded to one of the other two.

Rendering is delegated to `certkit.report.render()` rather than reimplemented here, because two
renderers eventually word the same refusal two ways.
