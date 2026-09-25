# Licensing

This repository holds the records that Ashforde OÜ (osaühing: a private
limited company registered in Estonia) publishes about the Aero Harness,
the private inspection runtime it operates, and a verifier for them. That is
two kinds of work, under two licences. The records are data and prose, so
they are licensed the way data and prose usually are: under the Creative
Commons Attribution 4.0 International licence (CC BY 4.0). The verifier is
code, so it is licensed the way code usually is: under the Apache License,
Version 2.0 (Apache-2.0).

> This page explains the terms in plain language. It is a guide, not legal
> advice, and it does not change the licences. The binding terms are the
> licence texts themselves: [`LICENSE`](LICENSE) and
> [`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt). Where this page and a
> licence text differ, the licence text governs.

## Which licence covers which file

| Files | Licence | Text |
|---|---|---|
| The records: `CALIBRATION.md`, everything under `calibration/` and `log/`, `README.md`, `family.json`, the figures under `assets/`, `CITATION.cff`, `NOTICE`, `SHA256SUMS`, and the other documents at the root that Ashforde OÜ wrote (`LICENSING.md`, `SECURITY.md`, `CONTRIBUTING.md`) | Creative Commons Attribution 4.0 International (CC BY 4.0) | [`LICENSE`](LICENSE) |
| The verifier and the automation: everything under `verify/`, the files under `.github/`, `.gitattributes`, `.ci-native` and `.ci-policy` | Apache License, Version 2.0 | [`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt) |
| `CODE_OF_CONDUCT.md` | The Contributor Covenant, version 2.1, used under its own terms (CC BY 4.0, from its authors) | the file itself |
| The licence texts in `LICENSE` and `LICENSES/` | Reproduced unmodified from their publishers; they are not licensed by Ashforde OÜ | — |

Every file under `verify/` also carries, in its first lines, a licence
identifier in the SPDX (Software Package Data Exchange) form,
`SPDX-License-Identifier: Apache-2.0`, so a copy of one file taken on its own
still says what it is.

## The records: CC BY 4.0

You may copy, redistribute, quote, adapt and build on the records, for any
purpose, commercial or not, provided you give attribution. The attribution
we ask for is:

> Ashforde OÜ, Aero Harness operator records,
> https://github.com/ashfordeOU/aero-harness-records

with the commit or the date of the state you used, since the records change
every week. If you changed anything, say so: CC BY 4.0 requires a modified
copy to indicate that it was modified (section 3(a)(1)(B)).

CC BY 4.0 also licenses the database right that European Union (EU) law
gives the maker of a database (its section 4), so the records may be
extracted and reused as a whole on the same terms.

## The verifier: Apache-2.0

You may use, copy, modify and distribute the verifier, including inside
closed products, under the Apache License 2.0: keep the licence and the
notices, and say which files you changed. The licence includes a patent
grant from each contributor, which is the usual reason to prefer it for code.

## Telling a copy from the original

Nothing stops a copy from being altered, and neither licence tries to. Three
things let anyone tell an altered copy from the original:

- `SHA256SUMS` in this repository, at a given commit, names the digest of
  every other file in that commit under SHA-256 (Secure Hash Algorithm,
  256-bit). A copy that disagrees with it is not that commit's copy.
- The evidence log proves its own history: every checkpoint's root is
  recomputed from the leaves, every checkpoint names the digest of the one
  before it, and a checkpoint altered after it was stamped no longer matches
  its timestamp token.
- This repository's own history is public, so a record that was changed
  after it was published shows as a change to anyone who compares the
  history with an earlier clone.

## Names and marks

Neither licence grants any right to use the names "Aero Harness", "ARCS"
(the Agent Run Conformance Specification) or "Ashforde", or any mark.
Apache-2.0 says so in its section 6, and CC BY 4.0 in its section 2(b)(2). You may say truthfully that your work uses or
reproduces these records; you may not present your work as Ashforde OÜ's, or
as endorsed by it.

## Contributions

The files here are generated, so this repository does not merge pull
requests ([`CONTRIBUTING.md`](CONTRIBUTING.md) says why and what to do
instead). If you send a proposed change to the verifier, you offer it under
Apache-2.0, as its section 5 provides, unless you explicitly state
otherwise.

## Questions

Licensing questions go to contact@ashforde.org.
