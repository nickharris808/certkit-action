# Changelog

All notable changes to this package. Format follows [Keep a Changelog](https://keepachangelog.com/);
versioning is [semantic](https://semver.org/).

## [0.2.0]

### Added
- `sarif` input: writes a SARIF 2.1.0 report so refusals reach the GitHub Security tab instead of
  only the job log. Two declared rules, `certkit/refused` and `certkit/unverified`.
- `certkit-ref` input: pin certkit to a branch, tag, or commit SHA. This is the pinning mechanism
  that works, because certkit is not on PyPI.

### Changed
- SARIF emission now delegates to `certkit.report`, so a finding is worded identically here and in
  `certkit check --format sarif`. A fallback keeps SARIF working when `certkit-ref` pins an older
  certkit.
- `certkit-version` (PyPI specifier) now fails with an explanation pointing at `certkit-ref`.
  The README previously told users to set `certkit-version: "==0.1.0"`, which 404s.
- The runner distinguishes `UNVERIFIED` from `REFUSED` in its output and summary.

## [0.1.0]
- First release: composite action, glob support, counting mode, job summary, inline annotations.
