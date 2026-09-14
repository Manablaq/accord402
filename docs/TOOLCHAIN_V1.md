# Accord402 Toolchain V1

Status: FROZEN
Certified at: 2026-09-11T03:38:40Z

## Runtime

- Python: 3.12.14
- pip: 26.2.1
- pytest: 9.1.1
- GenLayer CLI: 0.39.2
- GenVM release: v0.6.0-rc5
- GenVM bundle SHA-256: bd30580f911338d5533460eca8ed714dec371de5803c04e41dbb96430aea7b6e
- GenVM bundle bytes: 325563524
- py-genlayer runner: py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6

## Exact source revisions

- genlayer-py version: 0.18.0
- genlayer-py commit: a3dc35e04898e3889cbfa855bcaf7d2664675b8f
- genlayer-test version: 0.29.2
- genlayer-test commit: 9c09578b143905471fb0657dd53bdaf18da8e35f
- genvm-linter version: 0.11.1rc2
- genvm-linter commit: 28450e665666300fc648dbe495110dfd0cb6a7b4

## Repository lock artifacts

- requirements-dev.txt SHA-256: 9e287221b592dd0bce0992ff3c3a58bc38432f7cab284c8341a67c1f7e689efa
- requirements-lock.txt SHA-256: 99e923899428aa788a05c1dd0241aea3cc7bd4792fcf53a62b6867c31d48855a

## Adjudication certification evidence

- checker SHA-256: 09a7dbd07ebdcba03c7d7b004620198fce4c4d3b54d5286a966ab13bc24df03a
- reference wire SHA-256: 5b2f175973c8bb8eda1b7208f19bbbfd9aa2d39db8d6c8c67b1fb2520a255b2a

The checker and reference-wire hashes above identify inputs/results of the
previous adjudication-wire certification gate. They are not classified
as frozen repository files by this toolchain freeze.

## Compatibility certification

The exact selected toolchain passed:
- VCS package identity verification
- runner artifact resolution
- GenVM AST lint
- SDK validation
- full GenVM check
- type checking
- pip dependency checking

A newer py-genlayer runner notice does not modify Toolchain V1.
The explicitly validated runner hash above remains frozen.

## Reproduction

Use Python 3.12.14, pin pip 26.2.1, and install
requirements-lock.txt into a fresh virtual environment.

Set GENVM_SOURCE_MODE=release.
Set GENVM_VERSION=v0.6.0-rc5.

## Freeze boundary

This freeze does not implement the Accord402 contract, modify any frozen
foundation artifact, authorize a runner migration, create a Git commit,
or authorize any blockchain transaction.
