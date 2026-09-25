#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ashforde OÜ
"""Each gate's calibration state at an instant, by the published policy.

A gate is one of the automated checks of the Aero Harness, the private
inspection runtime of Ashforde OÜ (osaühing, an Estonian private limited
company). The README states every gate's state as of the latest proof on
record, because a published page cannot know when it is read. This script
answers the question for the moment you run it, or for any instant you
name, by applying CALIBRATION.md to the files beside it:

  CALIBRATION.md            the interval, the grace, and the states, read
                            from the policy's own sentences
  calibration/registry.csv  every gate and its own interval in days
  calibration/log.csv       every proof: when, which gate, what outcome

For each gate, among the log's rows dated no later than the instant:

  * rows whose outcome is `void` are not proofs: a control that could not
    run proves nothing either way, and the last good proof keeps ageing;
  * if the latest remaining row is `out-of-tolerance`, the gate is
    out-of-tolerance;
  * otherwise, with no `red-capable` row it is lapsed; with one, it is
    current while the latest is no older than the gate's interval, stale
    for the grace after that, and lapsed from then on.

A RECORD YOU HOLD
-----------------
A record the runtime issues carries, in `provenance.calibration`, the state
of every gate at the instant it was issued, as the runtime computed it
then: its calibration annex. `--record` reads that annex and the record's
`issued_at`, applies the published policy to the published log at that
instant, and says for each gate whether the two agree. A record issued
before the runtime began writing the annex has none, the published specimen
among them; the script then prints NOT CHECKED and says why, rather than
guess, and exits 2. That is not a finding against the record.

The output names the instant the record was issued. Report a disagreement
privately (SECURITY.md), never in a public issue.

It reads the clock only when neither an instant nor a record is named.
Standard library only; Python 3.9 or later.

usage:
  python3 verify/gate_states.py
  python3 verify/gate_states.py --at 2026-10-01T00:00:00Z
  python3 verify/gate_states.py --record your-record.json

Exit 0 when no gate is lapsed or out of tolerance, or, with `--record`, when
every gate in the annex agrees with the log; 1 when one is lapsed or out of
tolerance (the policy then allows no record that depends on it to be
issued), when a gate in the annex disagrees, or when a row of the log or the
registry breaks the rules above; 2 when it could not run -- including when
the policy no longer states a figure in the sentence this script reads,
which is reported rather than guessed, and when the record carries no
annex to compare.
"""

import argparse
import csv
import datetime
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FMT = "%Y-%m-%dT%H:%M:%SZ"
INSTANT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

#: The policy's own sentences, as CALIBRATION.md words them.
INTERVAL_RE = re.compile(r"at least every \*\*(\d+) days\*\*")
GRACE_RE = re.compile(r"there is a \*\*(\d+)-day\*\* grace")
STATE_RE = re.compile(r"^-\s+`([a-z-]+)`\s+—", re.M)

#: The states this script computes. The policy must define exactly these.
STATES = ("current", "stale", "lapsed", "out-of-tolerance")
GOOD, BAD, VOID = "red-capable", "out-of-tolerance", "void"
OUTCOMES = (GOOD, BAD, VOID)


class CannotRun(Exception):
    pass


class NoAnnex(CannotRun):
    """A record with nothing to compare: not a finding against it."""


def instant(text):
    if not INSTANT_RE.match(text or ""):
        raise CannotRun("%r is not an instant of the form "
                        "YYYY-MM-DDTHH:MM:SSZ" % text)
    return datetime.datetime.strptime(text, FMT).replace(
        tzinfo=datetime.timezone.utc)


def _read(path):
    try:
        with io.open(path, encoding="utf-8", newline="") as fh:
            return fh.read()
    except OSError as exc:
        raise CannotRun("%s: %s" % (path, exc.strerror or exc))


def _rows(text):
    body = "\n".join(line for line in text.splitlines()
                     if not line.lstrip().startswith("#"))
    return list(csv.DictReader(io.StringIO(body)))


def policy(text):
    """(interval days, grace days) from CALIBRATION.md's own sentences."""
    interval, grace = INTERVAL_RE.search(text), GRACE_RE.search(text)
    if not interval or not grace:
        raise CannotRun("CALIBRATION.md no longer states its %s in the "
                        "sentence this script reads; read the policy and "
                        "apply it by hand"
                        % ("interval" if not interval else "grace"))
    section = text.split("## States", 1)[-1].split("\n## ", 1)[0] \
        if "## States" in text else ""
    named = tuple(STATE_RE.findall(section))
    if set(named) != set(STATES):
        raise CannotRun("CALIBRATION.md defines the states %s and this "
                        "script computes %s"
                        % (", ".join(named) or "(none)", ", ".join(STATES)))
    return int(interval.group(1)), int(grace.group(1))


def registry(text):
    out = []
    for row in _rows(text):
        gate = (row.get("gate") or "").strip()
        try:
            days = int(row.get("interval_days") or "")
        except ValueError:
            raise CannotRun("the registry's interval for %s is not a number "
                            "of days" % (gate or "a gate"))
        out.append((gate, days))
    return out


def proofs(text):
    """(rows, findings): every log row, and anything wrong with its shape."""
    rows, findings, last = [], [], ""
    for n, row in enumerate(_rows(text), 2):
        at, outcome = row.get("at") or "", row.get("outcome") or ""
        if not INSTANT_RE.match(at):
            findings.append("calibration/log.csv line %d: %r is not an "
                            "instant" % (n, at))
            continue
        if outcome not in OUTCOMES:
            findings.append("calibration/log.csv line %d: outcome %r is none "
                            "of %s" % (n, outcome, ", ".join(OUTCOMES)))
            continue
        if at < last:
            findings.append("calibration/log.csv line %d is dated before the "
                            "line above it; the log is appended to, never "
                            "rewritten" % n)
        last = max(last, at)
        rows.append(row)
    return rows, findings


def states(gates, rows, at, grace_days):
    """{gate: (state, since, last good proof)} at the instant `at`."""
    out = {}
    stamp = at.strftime(FMT)
    for gate, days in gates:
        mine = [r for r in rows if r["gate"] == gate and r["at"] <= stamp
                and r["outcome"] != VOID]
        good = [r["at"] for r in mine if r["outcome"] == GOOD]
        last_good = good[-1] if good else None
        if mine and mine[-1]["outcome"] == BAD:
            out[gate] = ("out-of-tolerance", mine[-1]["at"], last_good)
            continue
        if last_good is None:
            out[gate] = ("lapsed", None, None)
            continue
        proven = instant(last_good)
        due = proven + datetime.timedelta(days=days)
        ends = due + datetime.timedelta(days=grace_days)
        if at <= due:
            out[gate] = ("current", None, last_good)
        elif at <= ends:
            out[gate] = ("stale", due.strftime(FMT), last_good)
        else:
            out[gate] = ("lapsed", ends.strftime(FMT), last_good)
    return out


def annex(path):
    """(issued_at, {gate: (state, last proven)}) from a record you hold."""
    try:
        with io.open(path, encoding="utf-8") as fh:
            record = json.load(fh)
    except (OSError, ValueError) as exc:
        raise CannotRun("%s cannot be read as a record: %s" % (path, exc))
    if not isinstance(record, dict):
        raise CannotRun("%s is not a record" % path)
    issued = record.get("issued_at")
    if not isinstance(issued, str) or not INSTANT_RE.match(issued):
        raise CannotRun("%s states no issued_at of the form "
                        "YYYY-MM-DDTHH:MM:SSZ" % path)
    provenance = record.get("provenance")
    annexed = provenance.get("calibration") \
        if isinstance(provenance, dict) else None
    gates = annexed.get("gates") if isinstance(annexed, dict) else None
    if not isinstance(gates, dict) or not gates:
        raise NoAnnex("%s carries no calibration annex "
                      "(provenance.calibration): it was issued before the "
                      "runtime began writing one, so there is nothing to "
                      "compare. This is not a finding against the record"
                      % path)
    out = {}
    for gate, row in gates.items():
        row = row if isinstance(row, dict) else {}
        out[gate] = (row.get("state"), row.get("last_proven"))
    return issued, out


def compare(claimed, result):
    """Findings where a record's annex and the published log disagree."""
    out = []
    for gate in sorted(claimed):
        state, last = claimed[gate]
        if gate not in result:
            out.append("%s: the record states %s, and the published registry "
                       "has no such gate" % (gate, state))
            continue
        have, _since, have_last = result[gate]
        if (state, last) != (have, have_last):
            out.append("%s: the record states %s, last proven %s; the "
                       "published log gives %s, last proven %s"
                       % (gate, state, last or "never", have,
                          have_last or "never"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="gate_states.py",
        description="Each gate's calibration state at an instant, by the "
                    "policy published beside it.")
    which = ap.add_mutually_exclusive_group()
    which.add_argument("--at", help="the instant, YYYY-MM-DDTHH:MM:SSZ "
                                    "(default: now)")
    which.add_argument("--record", help="a record you hold: check its "
                                        "calibration annex against the log")
    ap.add_argument("--records", default=os.path.dirname(HERE),
                    help="the records' root (default: this repository)")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    claimed = None
    try:
        if args.record:
            issued, claimed = annex(args.record)
            at = instant(issued)
        else:
            at = instant(args.at) if args.at else datetime.datetime.now(
                datetime.timezone.utc).replace(microsecond=0)
        interval, grace = policy(_read(os.path.join(args.records,
                                                    "CALIBRATION.md")))
        gates = registry(_read(os.path.join(args.records, "calibration",
                                            "registry.csv")))
        rows, findings = proofs(_read(os.path.join(args.records,
                                                   "calibration", "log.csv")))
    except NoAnnex as exc:
        print("NOT CHECKED gate-states: %s" % exc)
        return 2
    except CannotRun as exc:
        print("FAIL gate-states: could not run: %s" % exc)
        return 2
    for gate, days in gates:
        if days > interval:
            findings.append("%s is registered with an interval of %d days; "
                            "the policy allows at most %d"
                            % (gate, days, interval))
    result = states(gates, rows, at, grace)
    when = at.strftime(FMT)
    print("Policy (CALIBRATION.md): re-proven at least every %d days, then "
          "a %d-day grace. State of each gate at %s:" % (interval, grace,
                                                          when))
    width = max([len(g) for g, _ in gates] + [4])
    for gate, _ in gates:
        state, since, last_good = result[gate]
        detail = "last proven %s" % last_good if last_good else \
            "never proven"
        if since:
            detail += "; %s since %s" % (state, since)
        print("  %-*s  %-16s  %s" % (width, gate, state, detail))
    counts = dict((s, sum(1 for v in result.values() if v[0] == s))
                  for s in STATES)
    summary = ", ".join("%d %s" % (counts[s], s) for s in STATES)
    for f in findings:
        print("FAIL gate-states: %s" % f)
    if findings:
        return 1
    if claimed is not None:
        differ = compare(claimed, result)
        for f in differ:
            print("FAIL gate-states: %s" % f)
        if differ:
            print("FAIL gate-states: %d of %d gate(s) in the record's "
                  "calibration annex disagree with the published log at its "
                  "issue, %s" % (len(differ), len(claimed), when))
            return 1
        print("PASS gate-states: all %d gate(s) in the record's calibration "
              "annex agree with the published log at its issue, %s."
              % (len(claimed), when))
        return 0
    if counts["lapsed"] or counts["out-of-tolerance"]:
        print("FAIL gate-states: %d gate(s) at %s: %s. The policy allows no "
              "record that depends on a lapsed or out-of-tolerance gate to "
              "be issued." % (len(gates), when, summary))
        return 1
    print("PASS gate-states: %d gate(s) at %s: %s."
          % (len(gates), when, summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
