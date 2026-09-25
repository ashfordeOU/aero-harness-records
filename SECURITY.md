# Security Policy

This policy covers the integrity of the records that Ashforde OÜ (osaühing:
a private limited company registered in Estonia) publishes about the Aero
Harness, the private inspection runtime it operates: the files in this
repository, `SHA256SUMS`, the evidence log under `log/`, the verifier under
`verify/`, and the workflow under `.github/`. The records are published so
that anyone can check them; a way to defeat that check is the most serious
report this repository can receive.

## Reporting privately

Report the following **privately**. Do not open a public issue or pull request
that describes them before they are resolved.

- A way to alter a published record, the log or its history so that the
  checks this repository publishes do not notice.
- A defect in the verifier that makes it pass a log it should refuse, or
  refuse one it should pass.
- Anything that would let someone learn from the log what a record contains,
  who holds it, or how many records were issued, or that would let a
  record's serial (its `record_id`, the identifier that appears on it) seen
  elsewhere be looked up in the log without the salt its record carries.
- A record you hold that you cannot find in the log, or whose calibration
  annex (the state of every gate at the instant of issue, which the record
  carries in `provenance.calibration`) `verify/gate_states.py --record` finds
  in disagreement with the published log. Your record, its serial, its salt
  and the instant it was issued are yours: do not post them in a public
  issue. The script's output names that instant, so do not paste it in
  public either.

The private channel is email: **contact@ashforde.org**, with "RECORDS" in
the subject.

Discrepancies that reveal nothing private — a checksum that does not match,
a figure in the README that the files do not support — are better reported
in the open, with the discrepancy form under Issues, so that anyone can see
them and the answer.

## What to include

- The commit of this repository you checked (`git rev-parse HEAD`).
- The command you ran, its full output, and what you expected instead.
- For a verifier defect, the smallest pair of files that shows it.
- Optional contact details for follow-up.

## What happens next

Reports are read by the operator, Ashforde OÜ. A report that shows a gate
could not detect what its proof says it detected is a failed proof, and
[`CALIBRATION.md`](CALIBRATION.md), in "What a failed proof does to records
already issued", says what follows. A defect in the verifier is fixed in
the verifier. We do not disclose a report before it is resolved, and if it
cannot be resolved we agree the disclosure with the reporter rather than
stay silent. Reporters are credited unless they ask not to be.

## Scope

In scope: every file in this repository, and the process that produces it,
as far as this repository describes it. The Aero Harness runtime that
builds these files is private and outside this repository; a report about
it may be sent through the same private channels.

This repository holds no secrets, no credentials and no record's content.
If you find one here, that is itself a report.
