#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ashforde OÜ
"""Check the Aero Harness evidence log from its two public files.

The Aero Harness is the private inspection runtime of Ashforde OÜ
(osaühing, an Estonian private limited company). Its evidence log is an
append-only log of commitments to the records the runtime issues. This
script checks that log with nothing but Python. It was written from the
format this repository's README documents (section "Evidence log") and,
for the tree, from RFC 9162 (Request for Comments 9162, Certificate
Transparency Version 2.0), section 2.1, which restates the Merkle tree of
RFC 6962 (Certificate Transparency). It does not use, and does not need,
the operator's runtime: a log that only its operator's code can check is a
log nobody else can rely on.

WHAT IT CHECKS
--------------
In log/leaves.txt, that every line is one commitment: 64 lowercase
hexadecimal characters. In log/checkpoints.jsonl, that every line is one
JSON (JavaScript Object Notation) object, and then, for checkpoint n,
counting from 1:

  * its `context` is the log's context string and its `sequence` is n;
  * its `batch` is the batch size, and its `tree_size` is n batches;
  * its `root` is the Merkle tree root of the first `tree_size` leaves;
  * the batch it added is sorted by value;
  * its `previous` is the digest of checkpoint n - 1, or null for n = 1;
  * its `consistency_from_previous` proves that its tree extends the tree
    of checkpoint n - 1 (and is empty for n = 1);
  * its `at` is an instant in Coordinated Universal Time (UTC), no earlier
    than the previous checkpoint's;
  * when its timestamp is `stamped`, the token is a timestamp token of
    RFC 3161 (Internet X.509 Public Key Infrastructure Time-Stamp
    Protocol; X.509 is the standard format of public-key certificates)
    whose message imprint carries this checkpoint's digest as its hashed
    message and names SHA-256 (Secure Hash Algorithm, 256-bit) as its hash
    algorithm, and whose time is the time the checkpoint states.

Last, that leaves.txt holds exactly as many leaves as the last checkpoint
covers: no leaf that no checkpoint vouches for, and none removed.

WHAT IT DOES NOT CHECK
----------------------
The timestamp token's signature, and the chain from the time-stamping
authority's certificate to a root you trust. That needs X.509
certificates and the RSA (Rivest-Shamir-Adleman) or ECDSA (Elliptic Curve
Digital Signature Algorithm) signature schemes, which Python's standard
library does not have. `--export-tokens` writes each token to a file and
prints the command of OpenSSL, the widely used open-source cryptography
toolkit, that checks it.
It does not check `status_list` either: the status list it names is not
published in this repository.

A RECORD YOU HOLD
-----------------
`--record` reads a record's `record_id` and `provenance.log.salt`,
computes its commitment, finds it under the latest checkpoint, and prints
an inclusion proof checked against that checkpoint's root. `--leaf` does
the same for a commitment you already have. Nothing leaves your machine.

usage:
  python3 verify/verify_log.py log/
  python3 verify/verify_log.py log/ --record your-record.json
  python3 verify/verify_log.py log/ --leaf <64 hexadecimal characters>
  python3 verify/verify_log.py log/ --export-tokens <a directory>

Standard library only; Python 3.9 or later. Exit 0 when the log holds (and
the record or leaf asked about is in it), 1 on a finding, 2 when it could
not run.
"""

import argparse
import base64
import hashlib
import io
import json
import os
import re
import sys

LEAVES_FILE = "leaves.txt"
CHECKPOINTS_FILE = "checkpoints.jsonl"

#: The documented constants of the format.
CONTEXT = "aero-evidence-log-checkpoint/v1"
LEAF_TAG = b"aero-evidence-log-leaf/v1"
BATCH = 16
#: Fields a checkpoint's digest leaves out: they are added after it.
OUTSIDE_DIGEST = ("timestamp", "attestation")
STAMP_STATES = ("stamped", "unavailable", "not_requested")

COMMITMENT_RE = re.compile(r"^[0-9a-f]{64}$")
INSTANT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

OID_SIGNED_DATA = "1.2.840.113549.1.7.2"
OID_TST_INFO = "1.2.840.113549.1.9.16.1.4"
OID_SHA256 = "2.16.840.1.101.3.4.2.1"

OPENSSL = ("openssl ts -verify -digest {digest} -in {token} -token_in "
           "-CAfile <your trusted root certificates>")


class Unreadable(Exception):
    """A file the log is made of is missing or cannot be read at all."""


# -- RFC 9162, section 2.1 ----------------------------------------------------

def _h(data):
    return hashlib.sha256(data).digest()


def leaf_hash(entry):
    return _h(b"\x00" + entry)


def node_hash(left, right):
    return _h(b"\x01" + left + right)


def _largest_power_of_two_below(n):
    k = 1
    while k * 2 < n:
        k *= 2
    return k


def merkle_root(entries):
    """The Merkle tree hash of the entries themselves, not yet
    leaf-hashed: the function RFC 9162 section 2.1 writes MTH(D[n])."""
    if not entries:
        return _h(b"")
    if len(entries) == 1:
        return leaf_hash(entries[0])
    k = _largest_power_of_two_below(len(entries))
    return node_hash(merkle_root(entries[:k]), merkle_root(entries[k:]))


def inclusion_path(index, entries):
    """The audit path for entries[index]: the function RFC 9162
    section 2.1 writes PATH(m, D[n])."""
    if len(entries) <= 1:
        return []
    k = _largest_power_of_two_below(len(entries))
    if index < k:
        return inclusion_path(index, entries[:k]) + [merkle_root(entries[k:])]
    return (inclusion_path(index - k, entries[k:]) +
            [merkle_root(entries[:k])])


def inclusion_holds(entry, index, size, path, root):
    """RFC 9162 2.1.3.2, step by step."""
    if index >= size:
        return False
    fn, sn = index, size - 1
    r = leaf_hash(entry)
    for p in path:
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            r = node_hash(p, r)
            while fn and not fn & 1:
                fn >>= 1
                sn >>= 1
        else:
            r = node_hash(r, p)
        fn >>= 1
        sn >>= 1
    return sn == 0 and r == root


def consistency_holds(first_size, second_size, first_root, second_root,
                      proof):
    """RFC 9162 2.1.4.2, step by step, for 0 < first_size < second_size."""
    if not 0 < first_size < second_size or not proof:
        return False
    path = list(proof)
    if first_size & (first_size - 1) == 0:
        path.insert(0, first_root)
    fn, sn = first_size - 1, second_size - 1
    while fn & 1:
        fn >>= 1
        sn >>= 1
    fr = sr = path[0]
    for c in path[1:]:
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            fr = node_hash(c, fr)
            sr = node_hash(c, sr)
            while fn and not fn & 1:
                fn >>= 1
                sn >>= 1
        else:
            sr = node_hash(sr, c)
        fn >>= 1
        sn >>= 1
    return sn == 0 and fr == first_root and sr == second_root


# -- the format ---------------------------------------------------------------

def checkpoint_digest(checkpoint):
    """SHA-256, hex, over the checkpoint's canonical JSON, less the fields
    that are added after the digest is taken."""
    body = dict((k, v) for k, v in checkpoint.items()
                if k not in OUTSIDE_DIGEST)
    text = json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def commitment(record_id, salt_hex):
    """The leaf a record is logged under."""
    return _h(LEAF_TAG + b"\x00" + record_id.encode("utf-8") + b"\x00" +
              bytes.fromhex(salt_hex))


def _read_text(path):
    try:
        with io.open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        raise Unreadable("%s: %s" % (path, exc.strerror or exc))
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        # The public files are text in the Unicode transformation
        # format UTF-8, and nothing else is read as them.
        raise Unreadable("%s is not UTF-8" % path)


def _lines(text):
    """(lines, findings) for a file that ends every line with a newline."""
    if not text:
        return [], []
    if text.endswith("\n"):
        return text[:-1].split("\n"), []
    return text.split("\n"), ["the last line has no newline, so the file "
                               "was cut short or written by something else"]


def read_log(log_dir):
    """(leaves, checkpoints, findings) from the two public files."""
    findings = []
    text = _read_text(os.path.join(log_dir, LEAVES_FILE))
    lines, bad = _lines(text)
    findings += ["%s: %s" % (LEAVES_FILE, b) for b in bad]
    leaves = []
    for n, line in enumerate(lines, 1):
        if not COMMITMENT_RE.match(line):
            findings.append("%s line %d is not a commitment (64 lowercase "
                            "hexadecimal characters): %r"
                            % (LEAVES_FILE, n, line[:70]))
            leaves.append(None)
        else:
            leaves.append(bytes.fromhex(line))
    text = _read_text(os.path.join(log_dir, CHECKPOINTS_FILE))
    lines, bad = _lines(text)
    findings += ["%s: %s" % (CHECKPOINTS_FILE, b) for b in bad]
    checkpoints = []
    for n, line in enumerate(lines, 1):
        try:
            value = json.loads(line)
        except ValueError:
            value = None
        if not isinstance(value, dict):
            findings.append("%s line %d is not one JSON object"
                            % (CHECKPOINTS_FILE, n))
            value = {}
        checkpoints.append(value)
    return leaves, checkpoints, findings


# -- RFC 3161 tokens, read far enough to find the imprint and the time --------

def _der(data, start, end):
    """[(tag, body start, body end)] for the tag-length-value items of
    the Distinguished Encoding Rules (DER), laid end to end."""
    out, i = [], start
    while i < end:
        if i + 2 > end:
            raise ValueError("a DER header runs past its container")
        tag, size = data[i], data[i + 1]
        i += 2
        if size & 0x80:
            count = size & 0x7F
            if not 1 <= count <= 4 or i + count > end:
                raise ValueError("a DER length is malformed")
            size = int.from_bytes(data[i:i + count], "big")
            i += count
        if i + size > end:
            raise ValueError("a DER value runs past its container")
        out.append((tag, i, i + size))
        i += size
    return out


def _only(data, start, end, tag, what):
    items = _der(data, start, end)
    if len(items) != 1 or items[0][0] != tag:
        raise ValueError("%s is not where RFC 3161 puts it" % what)
    return items[0]


def _oid(data, start, end):
    body = data[start:end]
    if not body:
        raise ValueError("an empty object identifier")
    parts = [min(body[0] // 40, 2)]
    parts.append(body[0] - 40 * parts[0])
    value = 0
    for byte in body[1:]:
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            parts.append(value)
            value = 0
    return ".".join(str(p) for p in parts)


def read_token(der):
    """(the object identifier of the imprint's hash algorithm, the
    imprint bytes, the time as YYYY-MM-DDTHH:MM:SSZ).

    ContentInfo -> SignedData -> encapContentInfo -> TSTInfo -> the
    messageImprint and genTime. Nothing is verified here but the shape.
    """
    ci = _only(der, 0, len(der), 0x30, "the ContentInfo")
    ci_items = _der(der, ci[1], ci[2])
    if len(ci_items) < 2 or ci_items[0][0] != 0x06 or \
            _oid(der, ci_items[0][1], ci_items[0][2]) != OID_SIGNED_DATA:
        raise ValueError("the token is not a Cryptographic Message "
                         "Syntax SignedData object")
    sd = _only(der, ci_items[1][1], ci_items[1][2], 0x30, "the SignedData")
    sd_items = _der(der, sd[1], sd[2])
    if len(sd_items) < 3 or sd_items[2][0] != 0x30:
        raise ValueError("the SignedData has no encapsulated content")
    encap = _der(der, sd_items[2][1], sd_items[2][2])
    if len(encap) != 2 or encap[0][0] != 0x06 or \
            _oid(der, encap[0][1], encap[0][2]) != OID_TST_INFO:
        raise ValueError("the signed content is not a TSTInfo")
    octets = _only(der, encap[1][1], encap[1][2], 0x04, "the TSTInfo")
    tst = der[octets[1]:octets[2]]
    info = _only(tst, 0, len(tst), 0x30, "the TSTInfo")
    fields = _der(tst, info[1], info[2])
    if len(fields) < 5 or fields[2][0] != 0x30 or fields[4][0] != 0x18:
        raise ValueError("the TSTInfo is missing its imprint or its time")
    imprint = _der(tst, fields[2][1], fields[2][2])
    if len(imprint) != 2 or imprint[0][0] != 0x30 or imprint[1][0] != 0x04:
        raise ValueError("the message imprint is malformed")
    algorithm = _der(tst, imprint[0][1], imprint[0][2])
    if not algorithm or algorithm[0][0] != 0x06:
        raise ValueError("the message imprint names no algorithm")
    alg = _oid(tst, algorithm[0][1], algorithm[0][2])
    hashed = tst[imprint[1][1]:imprint[1][2]]
    gen = tst[fields[4][1]:fields[4][2]].decode("ascii")
    if len(gen) < 15 or not gen.endswith("Z") or not gen[:14].isdigit():
        raise ValueError("the token's time %r is not UTC" % gen)
    when = "%s-%s-%sT%s:%s:%sZ" % (gen[0:4], gen[4:6], gen[6:8], gen[8:10],
                                   gen[10:12], gen[12:14])
    return alg, hashed, when


# -- the audit ----------------------------------------------------------------

def _hex_list(value):
    if not isinstance(value, list):
        return None
    out = []
    for item in value:
        if not isinstance(item, str) or not COMMITMENT_RE.match(item):
            return None
        out.append(bytes.fromhex(item))
    return out


def check_timestamp(where, checkpoint, digest_hex):
    """(findings, token bytes or None, state)."""
    stamp = checkpoint.get("timestamp")
    if not isinstance(stamp, dict) or \
            stamp.get("state") not in STAMP_STATES:
        return (["%s: its timestamp states none of %s"
                 % (where, ", ".join(STAMP_STATES))], None, None)
    state = stamp["state"]
    if state != "stamped":
        return [], None, state
    try:
        der = base64.b64decode(stamp.get("token") or "", validate=True)
        alg, hashed, when = read_token(der)
    except (ValueError, TypeError) as exc:
        return (["%s: its timestamp token cannot be read: %s"
                 % (where, exc)], None, state)
    out = []
    if alg != OID_SHA256 or hashed != bytes.fromhex(digest_hex):
        out.append("%s: its timestamp token stamps a different digest, so "
                   "the checkpoint was altered after it was stamped, or "
                   "the token belongs to another checkpoint" % where)
    if stamp.get("time") != when:
        out.append("%s: it states the stamp's time as %r and the token says "
                   "%s" % (where, stamp.get("time"), when))
    return out, der, state


def audit(leaves, checkpoints):
    """(findings, notes). Empty findings means the log holds."""
    out, notes = [], []
    previous = None
    for n, c in enumerate(checkpoints, 1):
        where = "checkpoint %d" % n
        if not c:
            previous = c
            continue
        if c.get("context") != CONTEXT:
            out.append("%s: its context is %r, not %r"
                       % (where, c.get("context"), CONTEXT))
        if c.get("sequence") != n:
            out.append("%s: it says it is sequence %r"
                       % (where, c.get("sequence")))
        if c.get("batch") != BATCH:
            out.append("%s: it states a batch of %r, not %d"
                       % (where, c.get("batch"), BATCH))
        at = c.get("at")
        if not isinstance(at, str) or not INSTANT_RE.match(at):
            out.append("%s: `at` is %r, not a UTC instant" % (where, at))
        elif n > 1 and isinstance(previous.get("at"), str) and \
                at < previous["at"]:
            out.append("%s: it is dated %s, before checkpoint %d (%s)"
                       % (where, at, n - 1, previous["at"]))
        if n == 1:
            if c.get("previous") is not None:
                out.append("%s: it names %r as a checkpoint before it, and "
                           "there is none" % (where, c.get("previous")))
        else:
            want = checkpoint_digest(previous)
            if c.get("previous") != want:
                out.append("%s: it names %r as the checkpoint before it, and "
                           "the digest of checkpoint %d is %s -- the chain "
                           "is broken" % (where, c.get("previous"), n - 1,
                                          want))
        size = c.get("tree_size")
        if size != n * BATCH:
            out.append("%s: it covers %r leaves, not %d: every checkpoint "
                       "adds exactly one batch of %d"
                       % (where, size, n * BATCH, BATCH))
        elif size > len(leaves):
            out.append("%s: it covers %d leaves and %s holds %d"
                       % (where, size, LEAVES_FILE, len(leaves)))
        elif any(leaf is None for leaf in leaves[:size]):
            out.append("%s: a leaf it covers cannot be read, so its root "
                       "cannot be recomputed" % where)
        else:
            root = merkle_root(leaves[:size])
            if root.hex() != c.get("root"):
                out.append("%s: the leaves it covers do not hash to its "
                           "root -- a leaf was altered, removed, inserted "
                           "or moved after it was published" % where)
            added = leaves[size - BATCH:size]
            if added != sorted(added):
                out.append("%s: the batch it added is not sorted, so its "
                           "order could say which leaf came first" % where)
            proof = _hex_list(c.get("consistency_from_previous"))
            if proof is None:
                out.append("%s: consistency_from_previous is not a list of "
                           "hashes" % where)
            elif n == 1 and proof:
                out.append("%s: the first checkpoint carries a consistency "
                           "proof, and there is no tree before it" % where)
            elif n > 1 and isinstance(previous.get("tree_size"), int) and \
                    isinstance(previous.get("root"), str) and \
                    COMMITMENT_RE.match(previous["root"]) and \
                    isinstance(c.get("root"), str) and \
                    COMMITMENT_RE.match(c["root"]):
                if not consistency_holds(
                        previous.get("tree_size"), size,
                        bytes.fromhex(previous["root"]),
                        bytes.fromhex(c["root"]), proof):
                    out.append("%s: its consistency proof does not show "
                               "that its tree extends checkpoint %d's"
                               % (where, n - 1))
            elif n > 1:
                out.append("%s: its consistency proof cannot be checked: "
                           "checkpoint %d or this one has no readable size "
                           "and root" % (where, n - 1))
        stamp_found, _, state = check_timestamp(where, c,
                                                checkpoint_digest(c))
        out += stamp_found
        notes.append((n, c, state))
        previous = c
    covered = checkpoints[-1].get("tree_size") if checkpoints else 0
    if isinstance(covered, int) and len(leaves) != covered:
        out.append("%s holds %d leaves and the last checkpoint covers %d: "
                   "leaves were written that no checkpoint vouches for, or "
                   "removed from under one"
                   % (LEAVES_FILE, len(leaves), covered))
    return out, notes


# -- a record you hold --------------------------------------------------------

def prove(leaves, checkpoints, entry):
    """(proof dict, findings) for a commitment under the latest checkpoint."""
    if not checkpoints:
        return None, ["the log has no checkpoint yet"]
    last = checkpoints[-1]
    size = last["tree_size"]
    covered = leaves[:size]
    if entry not in covered:
        return None, ["%s is not among the %d leaves the latest checkpoint "
                      "covers. A record is committed at the first checkpoint "
                      "after it is issued, so it may be too recent; or it "
                      "was never logged -- its provenance.log says which"
                      % (entry.hex(), size)]
    index = covered.index(entry)
    path = inclusion_path(index, covered)
    root = bytes.fromhex(last["root"])
    if not inclusion_holds(entry, index, size, path, root):
        return None, ["the inclusion proof does not verify against the "
                      "latest checkpoint's root"]
    return {"commitment": entry.hex(), "index": index, "tree_size": size,
            "root": last["root"], "checkpoint": last["sequence"],
            "inclusion": [p.hex() for p in path]}, []


def _record_commitment(path):
    try:
        with io.open(path, encoding="utf-8") as fh:
            record = json.load(fh)
    except (OSError, ValueError) as exc:
        raise Unreadable("%s cannot be read as JSON: %s" % (path, exc))
    rid = record.get("record_id") if isinstance(record, dict) else None
    log = ((record.get("provenance") or {}).get("log") or {}) \
        if isinstance(record, dict) else {}
    salt = log.get("salt") if isinstance(log, dict) else None
    if not isinstance(rid, str) or not rid or not isinstance(salt, str) or \
            not COMMITMENT_RE.match(salt):
        raise Unreadable("%s carries no record_id and provenance.log.salt, "
                         "so it has no leaf: it was not committed to the log"
                         % path)
    return commitment(rid, salt)


# -- the command --------------------------------------------------------------

def _count(n, one, many):
    return "%d %s" % (n, one if n == 1 else many)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="verify_log.py",
        description="Check the Aero Harness evidence log from its public "
                    "files, with nothing but Python.")
    ap.add_argument("log_dir", help="the directory holding leaves.txt and "
                                    "checkpoints.jsonl (log/ in this "
                                    "repository)")
    which = ap.add_mutually_exclusive_group()
    which.add_argument("--record", help="a record you hold: prove it is in "
                                        "the log")
    which.add_argument("--leaf", help="a commitment, as 64 hexadecimal "
                                      "characters: prove it is in the log")
    ap.add_argument("--export-tokens", metavar="DIR",
                    help="write each checkpoint's timestamp token into "
                         "that directory (DIR) "
                         "and print the command that checks its signature")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        leaves, checkpoints, findings = read_log(args.log_dir)
        entry = None
        if args.record:
            entry = _record_commitment(args.record)
        elif args.leaf:
            if not COMMITMENT_RE.match(args.leaf.lower()):
                raise Unreadable("--leaf takes 64 hexadecimal characters")
            entry = bytes.fromhex(args.leaf.lower())
    except Unreadable as exc:
        print("FAIL verify-log: could not run: %s" % exc)
        return 2
    found, notes = audit(leaves, checkpoints)
    findings += found
    stamped = 0
    for n, c, state in notes:
        if state == "stamped":
            stamped += 1
            stamp = "stamped by %s at %s" % (
                c["timestamp"].get("authority"),
                c["timestamp"].get("time"))
        else:
            stamp = "timestamp %s" % state
        print("  checkpoint %d  %s  %s leaves  root %s  %s"
              % (n, c.get("at"), c.get("tree_size"),
                 str(c.get("root"))[:16], stamp))
    if findings:
        for f in findings:
            print("FAIL verify-log: %s" % f)
        print("FAIL verify-log: %s against %s and %s"
              % (_count(len(findings), "finding", "findings"),
                 _count(len(checkpoints), "checkpoint", "checkpoints"),
                 _count(len(leaves), "leaf", "leaves")))
        return 1
    if not checkpoints:
        print("FAIL verify-log: the log has no checkpoint, so there is "
              "nothing to verify")
        return 1
    print("PASS verify-log: %s, %s. Every root recomputes from the leaves; "
          "every checkpoint adds one sorted batch of %d, names the one "
          "before it and proves its tree extends it; %d of %d checkpoints "
          "carry a timestamp token, and each token names its checkpoint's "
          "digest."
          % (_count(len(checkpoints), "checkpoint", "checkpoints"),
             _count(len(leaves), "leaf", "leaves"),
             BATCH, stamped, len(checkpoints)))
    print("NOT CHECKED: the timestamp tokens' signatures and certificate "
          "chains (--export-tokens DIR prints the OpenSSL command), "
          "and the "
          "status lists the checkpoints name.")
    if args.export_tokens:
        os.makedirs(args.export_tokens, exist_ok=True)
        print("To check each token's signature with OpenSSL 3, run:")
        for n, c, state in notes:
            if state != "stamped":
                continue
            name = os.path.join(args.export_tokens, "checkpoint-%d.tst" % n)
            with io.open(name, "wb") as fh:
                fh.write(base64.b64decode(c["timestamp"]["token"]))
            print("  " + OPENSSL.format(digest=checkpoint_digest(c),
                                        token=name))
    if entry is None:
        return 0
    proof, missing = prove(leaves, checkpoints, entry)
    if missing:
        print("FAIL verify-log: %s" % missing[0])
        return 1
    print(json.dumps(proof, indent=2, sort_keys=True))
    print("PASS verify-log: the commitment is leaf %d of %d under checkpoint "
          "%d, and its inclusion proof verifies against that checkpoint's "
          "root." % (proof["index"], proof["tree_size"],
                     proof["checkpoint"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
