# Contributing to certkit-action

## Logic goes in `verify.py`, never in `action.yml`

The `runs:` block calls a script for one reason: a script can be tested. If you find yourself adding
shell to `action.yml` beyond installing dependencies and invoking the script, put it in `verify.py`
and write a test for it instead.

## Test the side effects, not just the return value

The action communicates through `GITHUB_OUTPUT` and `GITHUB_STEP_SUMMARY`. Those are the interface a
user's workflow depends on, so changes to them need tests that read the files back — see the
`workspace` fixture.

## Exit codes are the contract

    0  everything accepted (or refusals with fail-on-refusal disabled)
    1  a certificate was refused
    2  usage error: missing input, no files matched, unreadable file

A usage error must never be reported as `1`, because a workflow cannot distinguish "your certificate
is bad" from "your glob was wrong" if both fail the same way.

## Adoption defaults matter

`fail-on-refusal` defaults to `true` because a gate that does not gate is theatre. But keep the
`false` path working and tested — it is how teams adopt this without a red build on day one.

## License

Contributions are accepted under Apache-2.0.
