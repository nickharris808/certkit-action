# Honest scope

## What this action does

Installs `certkit` from source, checks **every spec matched by the `spec` input** — which may be a
path or a glob such as `certs/*.spec.json` — against the certificate beside each one, renders the
results, and sets the job status. Nothing else.

Each certificate is inferred by replacing `.spec.json` with `.cert.json` unless `cert` is given
explicitly. A pattern that matches nothing is an **error**, not an empty pass: a gate that reports
success for having checked no files is the failure mode this whole toolkit is shaped against.

| Result | Job |
|---|---|
| `ACCEPTED` | pass |
| `REFUSED` | fail |
| `UNVERIFIED` | fail |
| usage error | fail |

## What a passing job means

That the certificate proves the guard implies the safety property **as written in the spec**, over
the domain **as written in the spec**. That is all. In particular it does not mean:

- **That your code is safe.** Nothing here reads your source. If the spec models the wrong check, the
  proof is a correct proof about the wrong thing.
- **That the arithmetic is machine arithmetic.** The relations are over the mathematical integers. A
  proof says nothing about a path where your program's arithmetic wraps.
- **That the whole repository is covered.** Only the files your pattern matched were checked, and
  a spec with no certificate beside it is reported rather than skipped.

## What it does not do

- **It does not produce certificates.** Something else has to supply the multipliers.
- **It does not scan.** There is no discovery step, no directory sweep, and no heuristics.
- **It does not comment on the pull request.** A refusal becomes a SARIF alert and a failed job.

## Known limitations

- **No discovery.** The action checks what your pattern matches; it does not go looking for specs
  you did not name.
- **Installs from git.** Until the package is on PyPI, `certkit-ref` pins a ref rather than a version.
- **SARIF needs permissions.** Without `security-events: write` the alert is silently not uploaded;
  the job still fails on a refusal, which is the load-bearing half.

Fuller detail on what the underlying checker does and does not establish is in
[`certkit/SCOPE.md`](https://github.com/nickharris808/certkit/blob/main/SCOPE.md).
