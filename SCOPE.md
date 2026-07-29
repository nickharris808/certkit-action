# Honest scope

## What this action does

Installs `certkit` from source, checks one spec/certificate pair, renders the result, and sets the
job status. Nothing else.

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
- **That the whole repository is covered.** One pair is one pair.

## What it does not do

- **It does not produce certificates.** Something else has to supply the multipliers.
- **It does not scan.** There is no discovery step, no directory sweep, and no heuristics.
- **It does not comment on the pull request.** A refusal becomes a SARIF alert and a failed job.

## Known limitations

- **One pair per invocation.** For a sweep, use the pre-commit hook or the CI templates in the
  `certkit` repository.
- **Installs from git.** Until the package is on PyPI, `certkit-ref` pins a ref rather than a version.
- **SARIF needs permissions.** Without `security-events: write` the alert is silently not uploaded;
  the job still fails on a refusal, which is the load-bearing half.

Fuller detail on what the underlying checker does and does not establish is in
[`certkit/SCOPE.md`](https://github.com/nickharris808/certkit/blob/main/SCOPE.md).
