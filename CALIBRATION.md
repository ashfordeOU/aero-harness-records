# The calibration and lapse policy

Version 3 · effective 2026-09-23 · supersedes: Version 2 (effective 2026-09-22)

Every gate in this runtime is inspection equipment (`docs/INSTRUMENT.md`). It
is worth relying on only while there is a dated record showing it could still
detect what it was built to detect. This document says how often that has to
be shown, and what happens to records already issued when it is not.

It was fixed in the runtime's history before the first calibration entry was
written, and published with the first entries. Fixing it first is the only
order in which it can be written honestly: after the first lapse, a lapse
policy is a defence of whatever was done that week, and the easiest thing to
do that week is nothing.

## What calibrating a gate means

A gate is calibrated by running its **control** — the procedure that plants
defects in front of it and requires it to name each one — and recording the
outcome with the instant it was run. The registry `contract/calibration.csv`
names the control for every gate, and `make calibrate` runs them and
appends one dated row per gate to `records/calibration-log.csv`. Nothing is
ever removed from that log: a record of control that can lose its bad entries
is not a record of control.

Every control here is written by us. That is self-calibration, and it is
called that (`docs/INSTRUMENT.md`, section 3).

## A control that also runs on every run

One control is not left to the calendar alone. Before the dispatcher starts
any agent, it plants advice in a throwaway archive and requires the
provenance check and the graph merge each to refuse it and name it as
advice (`docs/MEMBRANE.md`). Each stage is graded on its own, so a run in
which either accepts any of the plant does not start. That
plant is also registered here, as part of `gate-membrane`'s control, so it is
proven on the calendar like every other gate. A run that stops on it has
found the gate unable to detect what it was proven to detect: that is a
failed proof, and the section below applies to it as it does to any other.

## Interval and grace

Every gate is re-proven at least every **30 days**, whether or not anything
changed. The runtime changes; so does the machine it runs on, and the
interpreter under it. A gate proven on the day of a change and never again is
proven about a machine that no longer exists.

After the interval there is a **7-day** grace, and after the grace the gate
has lapsed. The two numbers are the ones `tools/gates/calibration_current.py`
uses, and `make gate-calibration` refuses to pass when this document and the
code disagree.

## States

At any instant each gate is in exactly one of these states, and they are
exactly the states `make gate-calibration` can report.

- `current` — the last proof went red where it should, and is no older than
  the interval. Records may be issued.
- `stale` — the last proof is past the interval but inside the grace. Records
  may still be issued, and each one says which gates were stale when it was
  issued and since when. Nothing is withdrawn: the equipment was not found
  wrong, only not yet re-checked.
- `lapsed` — the last proof is past the interval and the grace, or there has
  never been one. **No record may be issued** that depends on the gate until
  it is proven again. Records issued earlier stand, because nothing has shown
  them wrong; the lapse is recorded against the date it began.
- `out-of-tolerance` — the most recent proof did **not** go red where it
  should have. The equipment is found unable to detect what it was proven to
  detect. That is the `harness-defect` trigger of `docs/COUNTERMAND.md`, and
  the section below on what a failed proof does to records already issued
  applies.

This is a graded decay, not a cliff. Stale costs a sentence in each record.
Lapsed stops issuance and nothing else. Only a failed proof reaches back into
records already in customers' hands, and it reaches exactly as far as the
last proof that was good.

## What a failed proof does to records already issued

The affected set is every record issued **since the last good proof** that
depended on the gate. The gate may have been wrong for all of that time; it
cannot have been wrong before it, because the proof before it went red.

That set is withdrawn under `docs/COUNTERMAND.md` — within 72 hours of
confirmation, by a published signed list — and regraded at our cost with the
gate repaired and proven again. A record whose regrade reaches the same
conclusion is re-issued and supersedes the withdrawn one. The countermand
policy's rule holds here unchanged: the blast radius belongs to the gate, not
to the record, and the set is withdrawn before it is narrowed.

## Who is told, and how fast

- **A gate goes stale.** Nobody outside; the next record issued says so
  itself.
- **A gate lapses.** The calibration log carries a dated `lapsed` entry within
  one working day of the grace ending, and issuance stops for the records
  that depend on it.
- **A proof fails.** It is a countermand. The affected customers are told
  first, and telling them buys no delay: the 72-hour deadline is met by the
  published list, not by the message.

## One person, permanently

The rota this has to survive is one person. So a proof is one command that
runs in minutes, the registry runs it for every gate at once, and a machine
runs it every week without being asked. A missed week is invisible; six
missed weeks are a public, dated lapse. The interval and the grace
together are 37 days, so five missed weeks leave a gate `stale` and it is
the sixth that lapses it. Nothing in this policy depends on anyone
remembering, and nothing in it promises an availability target.

## Amendment

Versions are integers and increase. The effective date is the date of
publication, and a version never applies backwards: a gate's state on a
given day is read under the version in force that day.

This document is published (`make publish-records`). A published document
amended without a new version leaves two texts in readers' hands under one
name, with no diff anyone can point at, which is the defect this section
exists to prevent. The text under the version line is pinned by digest in
`contract/document-versions.csv` beside the version the line states, so an
amendment moves the digest and cannot leave the version behind.

- **Version 3**, effective 2026-09-23, changes wording only. Version 2 said
  the policy was published before the first calibration entry was written;
  the public repository was created after the first proofs had been run, so
  a reader who follows the published custody trail finds that sentence
  false. What is true, and all Version 3 claims, is that the policy was
  fixed in this runtime's history before any proof ran and published with
  the first entries. Version 3 also names the section on failed proofs
  instead of sending a reader to a numbered section this document does not
  have, drops one sentence that described no present practice, and sets the
  versions out as a list. It also corrects "One person, permanently",
  which said five missed weeks are a lapse: five missed weeks are 35 days
  and this document lapses a gate at 37. No interval, grace, state or
  consequence changed.
- **Version 2**, effective 2026-09-22, added one section, "A control that
  also runs on every run", and changed no other term. It states a control
  that was already being run and names where it is registered; it moves no
  interval, no grace and no state.
- **Version 1**, effective 2026-09-21, the first.
