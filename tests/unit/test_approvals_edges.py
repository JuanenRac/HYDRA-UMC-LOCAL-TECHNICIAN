# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - tests/unit/test_approvals_edges.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Edge cases of the signed approvals and the trust store: every way an approval, a key or a file can be wrong must refuse, never approve."""
import base64
import json
import random
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from hydra_umc_local_technician.policy import approvals
from hydra_umc_local_technician.policy.approvals import ApprovalError, TrustStore

try:
    import cryptography  # noqa: F401
    HAVE_CRYPTO = True
except ImportError:  # pragma: no cover - the CI installs the dev extra
    HAVE_CRYPTO = False

PROPOSAL = {"id": "p1", "steps": ["one", "two"]}
ACTION = "service.restart"
NOW = 1_700_000_000.0


def _key_b64(seed: int) -> str:
    return base64.b64encode(bytes(random.Random(seed).randrange(256) for _ in range(32))).decode("ascii")


@unittest.skipUnless(HAVE_CRYPTO, "needs the cryptography package")
class ApprovalFixture(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.private = self.dir / "keys" / "ops.key"
        self.public = self.dir / "keys" / "ops.pub.json"
        approvals.generate_keypair(self.private, self.public, "ops")
        self.alias, self.public_key = approvals.read_public_key_file(self.public)
        self.store = TrustStore(self.dir / "trust.json", {})
        self.store.add("ops", self.public_key)

    def signed(self, **overrides):
        document = approvals.sign_approval(self.private, "ops", ACTION, PROPOSAL, ttl_seconds=600, now=NOW)
        document.update(overrides)
        return document

    def verify(self, document=None, **kwargs):
        return approvals.verify_approval(
            document or self.signed(), PROPOSAL, ACTION, self.store, max_validity_seconds=3600, now=NOW + 10, **kwargs)


class VerifyRefusals(ApprovalFixture):
    def test_a_valid_approval_is_accepted_once_with_its_facts(self):
        record = self.verify()
        self.assertEqual((record.approved_by, record.action, record.signature_verified), ("ops", ACTION, True))

    def test_a_document_with_missing_or_extra_fields_is_refused(self):
        document = self.signed()
        missing = {k: v for k, v in document.items() if k != "nonce"}
        with self.assertRaisesRegex(ApprovalError, "documented fields"):
            self.verify(missing)
        with self.assertRaisesRegex(ApprovalError, "documented fields"):
            self.verify({**document, "extra": 1})
        with self.assertRaisesRegex(ApprovalError, "documented fields"):
            approvals.verify_approval(["not", "a", "dict"], PROPOSAL, ACTION, self.store, max_validity_seconds=60)  # type: ignore[arg-type]

    def test_wrong_types_and_versions_are_refused_before_any_signature_check(self):
        for field, value in (("version", 2), ("approver", 5), ("action", None), ("proposalSha256", 1), ("nonce", 3), ("signature", 9)):
            with self.assertRaisesRegex(ApprovalError, "wrong version or field types", msg=field):
                self.verify(self.signed(**{field: value}))

    def test_times_must_be_real_numbers_and_never_booleans(self):
        for field, value in (("issuedAt", "now"), ("expiresAt", None), ("issuedAt", True), ("expiresAt", False)):
            with self.assertRaisesRegex(ApprovalError, "must be numbers", msg=field):
                self.verify(self.signed(**{field: value}))

    def test_an_unknown_approver_and_a_tampered_document_are_refused(self):
        with self.assertRaisesRegex(ApprovalError, "nobody is trusted"):
            self.verify(self.signed(approver="stranger"))
        for field, value in (("expiresAt", NOW + 5000), ("nonce", "0" * 32), ("issuedAt", NOW - 1)):
            with self.assertRaisesRegex(ApprovalError, "signature does not match", msg=field):
                self.verify(self.signed(**{field: value}))

    def test_a_signature_that_is_not_base64_or_the_wrong_length_is_refused(self):
        for bad in ("***not base64***", base64.b64encode(b"short").decode("ascii")):
            with self.assertRaises(ApprovalError):
                self.verify(self.signed(signature=bad))

    def test_the_wrong_action_and_the_wrong_proposal_are_refused(self):
        with self.assertRaisesRegex(ApprovalError, "not 'service.stop'"):
            approvals.verify_approval(self.signed(), PROPOSAL, "service.stop", self.store, max_validity_seconds=3600, now=NOW)
        with self.assertRaisesRegex(ApprovalError, "another proposal"):
            approvals.verify_approval(self.signed(), {**PROPOSAL, "id": "p2"}, ACTION, self.store, max_validity_seconds=3600, now=NOW)

    def test_the_time_window_has_a_skew_an_expiry_and_a_ceiling(self):
        def at(moment, ceiling=3600):
            return approvals.verify_approval(self.signed(), PROPOSAL, ACTION, self.store, max_validity_seconds=ceiling, now=moment)
        at(NOW - approvals.CLOCK_SKEW_SECONDS)  # inside the allowed skew
        with self.assertRaisesRegex(ApprovalError, "future"):
            at(NOW - approvals.CLOCK_SKEW_SECONDS - 1)
        at(NOW + 600)  # the last second
        with self.assertRaisesRegex(ApprovalError, "expired"):
            at(NOW + 601)
        with self.assertRaisesRegex(ApprovalError, "longer than"):
            at(NOW, ceiling=599)

    def test_a_nonce_is_used_once_and_forgotten_after_it_expires(self):
        nonces = self.dir / "state" / "nonces.json"
        document = self.signed()
        self.verify(document, used_nonces=nonces)
        with self.assertRaisesRegex(ApprovalError, "already used"):
            self.verify(document, used_nonces=nonces)
        stored = json.loads(nonces.read_text(encoding="utf-8"))
        self.assertEqual(list(stored.values()), [NOW + 600])
        later = approvals.verify_approval(self.signed(), PROPOSAL, ACTION, self.store, max_validity_seconds=3600,
                                          used_nonces=nonces, now=NOW + 20)
        self.assertTrue(later.signature_verified)
        # the old nonce is purged once its expiry has passed, so the file never grows without bound
        fresh = approvals.sign_approval(self.private, "ops", ACTION, PROPOSAL, ttl_seconds=60, now=NOW + 5000)
        approvals.verify_approval(fresh, PROPOSAL, ACTION, self.store, max_validity_seconds=3600, used_nonces=nonces, now=NOW + 5001)
        self.assertEqual(len(json.loads(nonces.read_text(encoding="utf-8"))), 1)

    def test_a_damaged_nonce_file_refuses_instead_of_approving(self):
        nonces = self.dir / "nonces.json"
        for text in ("{not json", "[1, 2]", json.dumps({"a": "soon"})):
            nonces.write_text(text, encoding="utf-8")
            with self.assertRaises(ApprovalError, msg=text):
                self.verify(used_nonces=nonces)


class SigningRefusals(ApprovalFixture):
    def test_sign_refuses_an_empty_action_a_bad_validity_and_a_bad_alias(self):
        with self.assertRaisesRegex(ApprovalError, "action must be named"):
            approvals.sign_approval(self.private, "ops", "  ", PROPOSAL, ttl_seconds=60)
        for ttl in (0, -5):
            with self.assertRaisesRegex(ApprovalError, "validity must be positive"):
                approvals.sign_approval(self.private, "ops", ACTION, PROPOSAL, ttl_seconds=ttl)
        with self.assertRaisesRegex(ApprovalError, "alias is 1 to 64"):
            approvals.sign_approval(self.private, "bad alias!", ACTION, PROPOSAL, ttl_seconds=60)

    def test_sign_refuses_a_missing_or_corrupt_private_key(self):
        with self.assertRaisesRegex(ApprovalError, "private key cannot be read"):
            approvals.sign_approval(self.dir / "absent.key", "ops", ACTION, PROPOSAL, ttl_seconds=60)
        broken = self.dir / "broken.key"
        broken.write_text("not-base64-at-all!!\n", encoding="utf-8")
        with self.assertRaisesRegex(ApprovalError, "not valid base64"):
            approvals.sign_approval(broken, "ops", ACTION, PROPOSAL, ttl_seconds=60)
        broken.write_text(base64.b64encode(b"x" * 8).decode("ascii"), encoding="utf-8")
        with self.assertRaisesRegex(ApprovalError, "must be 32 bytes"):
            approvals.sign_approval(broken, "ops", ACTION, PROPOSAL, ttl_seconds=60)

    def test_generate_keypair_never_overwrites_and_never_writes_inside_a_git_tree(self):
        with self.assertRaisesRegex(ApprovalError, "already exists"):
            approvals.generate_keypair(self.private, self.dir / "other.pub.json", "ops")
        with self.assertRaisesRegex(ApprovalError, "already exists"):
            approvals.generate_keypair(self.dir / "other.key", self.public, "ops")
        tree = self.dir / "work"
        (tree / ".git").mkdir(parents=True)
        with self.assertRaisesRegex(ApprovalError, "outside any git working tree"):
            approvals.generate_keypair(tree / "sub" / "k.key", tree / "sub" / "k.pub.json", "ops")
        self.assertFalse((tree / "sub").exists())

    def test_the_private_key_file_is_owner_only_where_the_system_has_modes(self):
        import os
        if os.name == "nt":
            self.skipTest("POSIX modes only")
        self.assertEqual(self.private.stat().st_mode & 0o077, 0)


class TrustStoreEdges(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "trust.json"

    def test_a_missing_store_is_empty_and_a_saved_one_round_trips(self):
        self.assertEqual(TrustStore.load(self.path).keys, {})
        store = TrustStore(self.path, {})
        store.add("a", _key_b64(1))
        store.add("b.c-d_e", _key_b64(2))
        self.assertEqual(TrustStore.load(self.path).keys, {"a": _key_b64(1), "b.c-d_e": _key_b64(2)})

    def test_a_malformed_store_is_refused_in_every_shape(self):
        shapes = {
            "not json": "{oops",
            "a list": "[]",
            "no keys": json.dumps({"version": 1}),
            "keys is a list": json.dumps({"version": 1, "keys": []}),
            "another version": json.dumps({"version": 2, "keys": {}}),
            "a key that is not a string": json.dumps({"version": 1, "keys": {"a": 5}}),
            "a key that is not base64": json.dumps({"version": 1, "keys": {"a": "***"}}),
            "a key of the wrong length": json.dumps({"version": 1, "keys": {"a": base64.b64encode(b"x").decode("ascii")}}),
            "a bad alias": json.dumps({"version": 1, "keys": {"bad alias": _key_b64(3)}}),
        }
        for name, text in shapes.items():
            self.path.write_text(text, encoding="utf-8")
            with self.assertRaises(ApprovalError, msg=name):
                TrustStore.load(self.path)

    def test_an_alias_is_never_silently_repointed(self):
        store = TrustStore(self.path, {})
        store.add("a", _key_b64(1))
        self.assertEqual(store.add("a", _key_b64(1)), approvals.fingerprint(_key_b64(1)))  # the same key again is harmless
        with self.assertRaisesRegex(ApprovalError, "already trusts another key"):
            store.add("a", _key_b64(2))
        self.assertEqual(store.keys["a"], _key_b64(1))
        store.add("a", _key_b64(2), replace=True)
        self.assertEqual(store.keys["a"], _key_b64(2))

    def test_add_refuses_a_bad_alias_and_a_bad_key_without_touching_the_file(self):
        store = TrustStore(self.path, {})
        with self.assertRaises(ApprovalError):
            store.add("", _key_b64(1))
        with self.assertRaises(ApprovalError):
            store.add("a" * 65, _key_b64(1))
        with self.assertRaises(ApprovalError):
            store.add("a", "***")
        self.assertFalse(self.path.exists())

    def test_remove_and_export(self):
        store = TrustStore(self.path, {})
        store.add("a", _key_b64(1))
        destination = Path(self._tmp.name) / "out" / "a.pub.json"
        store.export("a", destination)
        self.assertEqual(approvals.read_public_key_file(destination), ("a", _key_b64(1)))
        with self.assertRaisesRegex(ApprovalError, "no key is trusted"):
            store.export("zzz", destination)
        store.remove("a")
        self.assertEqual(TrustStore.load(self.path).keys, {})
        with self.assertRaisesRegex(ApprovalError, "no key is trusted"):
            store.remove("a")


class PublicKeyFileEdges(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "key.json"

    def test_every_malformed_public_key_file_is_refused(self):
        key = _key_b64(7)
        bodies = {
            "not json": "{",
            "a list": "[]",
            "another algorithm": json.dumps({"algorithm": "rsa", "publicKey": key}),
            "a key that is not text": json.dumps({"algorithm": "ed25519", "publicKey": 3}),
            "a fingerprint that is not the key's": json.dumps({"algorithm": "ed25519", "publicKey": key, "fingerprint": "0000"}),
        }
        for name, text in bodies.items():
            self.path.write_text(text, encoding="utf-8")
            with self.assertRaises(ApprovalError, msg=name):
                approvals.read_public_key_file(self.path)
        with self.assertRaises(ApprovalError):
            approvals.read_public_key_file(Path(self._tmp.name) / "absent.json")

    def test_a_file_with_the_right_fingerprint_or_none_is_read(self):
        key = _key_b64(8)
        self.path.write_text(json.dumps({"algorithm": "ed25519", "publicKey": key, "fingerprint": approvals.fingerprint(key)}), encoding="utf-8")
        self.assertEqual(approvals.read_public_key_file(self.path), ("", key))
        self.path.write_text(json.dumps({"algorithm": "ed25519", "publicKey": key, "alias": "x"}), encoding="utf-8")
        self.assertEqual(approvals.read_public_key_file(self.path), ("x", key))


class SmallHelpers(unittest.TestCase):
    def test_check_alias_accepts_the_documented_set_and_nothing_else(self):
        for good in ("a", "A9", "x.y-z_w", "a" * 64):
            self.assertEqual(approvals.check_alias(good), good)
        for bad in ("", "a" * 65, "a b", "a/b", "ñ", "a\n"):
            with self.assertRaises(ApprovalError, msg=repr(bad)):
                approvals.check_alias(bad)

    def test_the_fingerprint_is_stable_grouped_and_checks_the_key_length(self):
        text = approvals.fingerprint(_key_b64(1))
        self.assertEqual(text, approvals.fingerprint(_key_b64(1)))
        self.assertEqual([len(part) for part in text.split(" ")], [4] * 8)
        self.assertNotEqual(text, approvals.fingerprint(_key_b64(2)))
        with self.assertRaises(ApprovalError):
            approvals.fingerprint(base64.b64encode(b"short").decode("ascii"))

    def test_the_proposal_digest_ignores_key_order_and_sees_every_change(self):
        a = approvals.proposal_digest({"x": 1, "y": [1, 2]})
        self.assertEqual(a, approvals.proposal_digest({"y": [1, 2], "x": 1}))
        self.assertNotEqual(a, approvals.proposal_digest({"x": 1, "y": [2, 1]}))
        self.assertNotEqual(a, approvals.proposal_digest({"x": 1, "y": [1, 2], "z": None}))
        self.assertEqual(len(a), 64)
        self.assertEqual(approvals.proposal_digest({"t": "ñ"}), approvals.proposal_digest({"t": "ñ"}))


if __name__ == "__main__":
    unittest.main()
