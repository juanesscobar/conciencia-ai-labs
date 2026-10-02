from dataclasses import asdict, replace
from datetime import timedelta
import json
import unittest

from ai_factory_lab.domain import GateObservation, canonical, digest
from ai_factory_lab.experiment import prepare, finish, FIXTURES
from ai_factory_lab.simulator import SimulatedGPUProvider, ThermalVerifier, diagnose
from ai_factory_lab.signals import SignalsAdapter, AdapterError, signal_payload, LocalHTTPTransport

MISSION = "00000000-0000-4000-8000-000000000001"


def approved(plan):
    return GateObservation("approved", plan.fingerprint, "FIXTURE_ONLY", "test-fixture-run")


class SimulatorTests(unittest.TestCase):
    def test_stale_clock_and_invalid_timestamps(self):
        p, plan, _ = prepare()
        p.clock += timedelta(seconds=60)
        with self.assertRaises(PermissionError):
            p.execute(plan, approved(plan))
        samples = p.query_metrics()[-3:]
        self.assertEqual(diagnose(samples[:2] + (replace(samples[2], timestamp="bad"),)), "UNKNOWN")

    def test_reproducibility_and_seed_effect(self):
        def run(seed):
            p, plan, data = prepare(seed)
            return finish(p, plan, data, approved(plan))
        self.assertEqual(canonical(run(7)), canonical(run(7)))
        self.assertNotEqual(run(7)["before"], run(8)["before"])

    def test_detection_and_success(self):
        p, plan, run = prepare()
        self.assertEqual(run["diagnosis"], "THERMAL_ANOMALY")
        result = finish(p, plan, run, approved(plan))
        self.assertEqual(result["result"], "PASS")
        self.assertTrue(result["final_state"]["admission_paused"])
        self.assertTrue(all(s["temperature_c"] < 75 for s in result["after"]))

    def test_absent_and_rejected_never_execute(self):
        for decision in [None, "rejected", "waiting_approval"]:
            p, plan, run = prepare()
            gate = None if decision is None else replace(approved(plan), decision=decision)
            result = finish(p, plan, run, gate)
            self.assertEqual(result["result"], "BLOCKED")
            self.assertEqual(p.operations, {})
            self.assertFalse(p.paused)

    def test_insufficient_evidence_even_with_approval(self):
        p, plan, run = prepare(missing=True)
        self.assertEqual(run["diagnosis"], "UNKNOWN")
        self.assertEqual(finish(p, plan, run, approved(plan))["result"], "BLOCKED_INSUFFICIENT_EVIDENCE")
        with self.assertRaises(PermissionError):
            p.execute(plan, approved(plan))

    def test_changed_target_parameters_revision_and_environment(self):
        p, plan, _ = prepare()
        for altered in [replace(plan, target="sim-node-002"), replace(plan, revision=1),
                        replace(plan, parameters=(("paused", False),)), replace(plan, environment="REAL")]:
            with self.assertRaises((PermissionError, ValueError)):
                p.execute(altered, approved(plan))
        self.assertFalse(p.paused)

    def test_changed_evidence_and_stale_revision(self):
        p, plan, _ = prepare()
        p.sample(90)
        with self.assertRaises(PermissionError):
            p.execute(plan, approved(plan))
        current = p.plan_action(p.query_metrics())
        p.revision += 1
        with self.assertRaises(PermissionError):
            p.execute(current, approved(current))

    def test_idempotency_and_no_mutable_operation_leak(self):
        p, plan, _ = prepare()
        first = p.execute(plan, approved(plan))
        first["status"] = "corrupted"
        self.assertEqual(p.execute(plan, approved(plan))["status"], "succeeded")
        self.assertEqual(p.revision, 1)
        self.assertEqual(len(p.operations), 1)
        with self.assertRaises(PermissionError):
            p.execute(plan, None)

    def test_verifier_fails_despite_successful_execution(self):
        p, plan, run = prepare()
        result = finish(p, plan, run, approved(plan), recovery=False)
        self.assertEqual(result["execution"]["status"], "succeeded")
        self.assertEqual(result["result"], "FAIL")
        self.assertEqual(ThermalVerifier().verify(plan, ())["status"], "UNKNOWN")

    def test_normal_and_duplicate_or_mixed_samples(self):
        p = SimulatedGPUProvider()
        normal = tuple(p.sample(60) for _ in range(3))
        self.assertEqual(diagnose(normal), "NORMAL")
        _, _, run = prepare()
        p, _, _ = prepare()
        samples = p.query_metrics()[-3:]
        self.assertEqual(diagnose((samples[0], samples[0], samples[2])), "UNKNOWN")
        self.assertEqual(diagnose(samples[:2] + (replace(samples[2], target="other"),)), "UNKNOWN")

    def test_versioned_fixture_and_static_gate_binding(self):
        _, plan, _ = prepare()
        gate = json.loads((FIXTURES / "gate-observation.json").read_text())
        self.assertEqual(gate["plan_hash"], plan.fingerprint)
        for number in range(2, 6):
            scenario = json.loads((FIXTURES / f"EXP-00{number}.json").read_text())
            self.assertEqual(scenario["status"], "fixture_only")


class AdapterTests(unittest.TestCase):
    def payload(self):
        _, _, run = prepare()
        return signal_payload(MISSION, run)

    def test_endpoint_and_acknowledgement(self):
        payload = self.payload()
        def transport(method, path, body):
            self.assertEqual((method, path), ("POST", "/api/v1/signals/"))
            self.assertIsInstance(body["evidences"][0]["content"], str)
            return 201, {"id": MISSION, "mission_id": MISSION, "type": body["type"],
                         "title": body["title"], "status": "new", "evidence": [{"kind": "data"}]}
        self.assertEqual(SignalsAdapter(transport).emit(payload)["delivery"], "acknowledged")

    def test_failures_never_report_delivery(self):
        for status, body in [(401, {}), (400, {}), (500, {}), (200, {}), (201, {}), (201, [])]:
            with self.assertRaises(AdapterError):
                SignalsAdapter(lambda *args: (status, body)).emit(self.payload())
        calls = []
        def timeout(*args):
            calls.append(1)
            raise TimeoutError("sensitive transport context")
        with self.assertRaisesRegex(AdapterError, "outcome UNKNOWN") as caught:
            SignalsAdapter(timeout).emit(self.payload())
        self.assertNotIn("sensitive", str(caught.exception))
        self.assertEqual(len(calls), 1)

    def test_nonlocal_transport_forbidden(self):
        for url in ["https://app.conciencia.software", "http://localhost.evil", "http://user@localhost", "http://localhost/path"]:
            with self.assertRaises(ValueError):
                LocalHTTPTransport(url, "unused-fixture")


if __name__ == "__main__":
    unittest.main()
