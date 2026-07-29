# Troubleshooting

## The action fails with exit code 3 and I do not understand why

Exit 3 is `UNVERIFIED`: the arithmetic checked out, but a required precondition was never
established — normally that the certificate is not bound to the spec by fingerprint. **This fails the
job on purpose.** In a gate, "declined to certify" and "refused" have the same consequence, and
treating 3 as a warning would let a merge proceed on a check that explicitly did not run.

## `ERROR: Could not find a version that satisfies the requirement certkit==0.1.0`

You are pinning `certkit-version`, which resolves against PyPI, where the package is not yet
published. Use `certkit-ref` instead — it pins a git ref:

```yaml
- uses: nickharris808/certkit-action@main
  with:
    spec: my.spec.json
    cert: my.cert.json
    certkit-ref: main        # or a tag or commit sha
```

## No alert appears in the Security tab

Three things must all be true: `permissions: security-events: write` on the job, the SARIF upload
step present, and the run happening on a branch code scanning is enabled for. A refusal on a fork PR
will not upload, because forks do not get write permissions — the job still fails, which is the part
that matters.

## The refusal reason is different from what I see locally

It should be identical; the action delegates rendering to `certkit.report`. If the wording differs,
the versions differ — pin `certkit-ref` to the same ref you have installed locally.

## The action passes but I do not believe it

Run the same check yourself; that is the entire point of the format:

```bash
pip install "certkit@git+https://github.com/nickharris808/certkit@main"
certkit check --spec my.spec.json --cert my.cert.json
```

The action has no privileged path. If your local run disagrees with CI, the inputs differ.

## Can it check every certificate in the repository?

Not yet — it takes one pair. For a directory sweep use the pre-commit hook or the GitLab/CircleCI
templates in the `certkit` repository, all of which fail when a `*.cert.json` has no `*.spec.json`
beside it rather than skipping it.
