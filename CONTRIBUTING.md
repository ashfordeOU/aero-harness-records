# Contributing

Thank you for reading the records closely enough to want to change
something. This page explains why this repository does not take pull
requests, and what to do instead.

## The records are generated

Every file here is built by the Aero Harness, the private inspection
runtime of Ashforde OÜ (osaühing: a private limited company registered in
Estonia), and a scheduled job on the operator's machine rebuilds and
commits the set every week. None of it is edited by hand, and the runtime
holds this repository to what it builds byte for byte: a file changed here,
even correctly, is a file that no longer matches its source, and the next
build would put the original back. So a pull request cannot be merged. That is not a judgement of the change; it is how the records keep
the property that makes them worth reading.

## What to do instead

- **Something here is wrong or inconsistent.** Open an issue with the
  discrepancy form (Issues → New issue → Report a discrepancy). Say which
  file, which commit (`git rev-parse HEAD`), the command you ran and what it
  printed. If the discrepancy is real, it is fixed at its source and the
  next build carries the fix.
- **A record you hold, or anything that should not be public.** Use the
  private channel in [`SECURITY.md`](SECURITY.md). Never put a record, its
  serial (its `record_id`, the identifier that appears on it), its salt or
  the instant it was issued in a public issue.
- **An improvement to the verifier.** Open an issue with the question and
  improvement form (Issues → New issue → Ask a question or suggest an
  improvement); a patch pasted into the issue is welcome. A proposed change
  to the verifier is offered under the Apache License, Version 2.0
  (Apache-2.0), as its section 5 provides, unless you explicitly state
  otherwise ([`LICENSING.md`](LICENSING.md)).
- **A question about how to read the records.** Open an issue with the same
  form; the answer helps the next reader too.

## What a correction looks like

Nothing is ever removed from the calibration log
([`CALIBRATION.md`](CALIBRATION.md)), and nothing in the evidence log can
be changed without breaking the proofs that bind it. A row found to be
wrong is therefore not deleted or edited: it stays where anyone can see it,
beside whatever the log records after it. A correction to prose or to the
verifier arrives in the next build, as an ordinary commit.

## Conduct

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).
