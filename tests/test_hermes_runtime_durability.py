from __future__ import annotations

import asyncio
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath("src"))

from circulatio.domain.errors import PersistenceError
from circulatio.hermes.idempotency import SQLiteIdempotencyStore
from circulatio.hermes.runtime import build_hermes_circulatio_runtime
from tests._helpers import FakeCirculatioLlm


class _SlowInterpretLlm(FakeCirculatioLlm):
    async def interpret_material(self, input_data: dict[str, object]) -> dict[str, object]:
        await asyncio.sleep(0.05)
        return await super().interpret_material(input_data)


class HermesRuntimeDurabilityTests(unittest.TestCase):
    def _close_runtime(self, runtime) -> None:
        runtime.close()

    def test_durable_repository_survives_restart(self) -> None:
        async def run() -> None:
            with tempfile.TemporaryDirectory() as tempdir:
                db_path = os.path.join(tempdir, "circulatio.db")
                first = build_hermes_circulatio_runtime(db_path=db_path, llm=FakeCirculatioLlm())
                try:
                    workflow = await first.service.create_and_interpret_material(
                        {
                            "userId": "user_1",
                            "materialType": "reflection",
                            "text": "I walked through a house and found a snake image returning after the conflict.",
                        }
                    )
                    proposal = next(
                        item
                        for item in workflow["pendingProposals"]
                        if item["action"] == "upsert_personal_symbol"
                    )
                    await first.service.approve_proposals(
                        user_id="user_1",
                        run_id=workflow["run"]["id"],
                        proposal_ids=[proposal["id"]],
                    )
                finally:
                    self._close_runtime(first)

                second = build_hermes_circulatio_runtime(db_path=db_path, llm=FakeCirculatioLlm())
                try:
                    symbols = await second.repository.list_symbols("user_1")
                    self.assertEqual(len(symbols), 1)
                    self.assertEqual(symbols[0]["canonicalName"], "snake")
                    self.assertEqual(symbols[0]["recurrenceCount"], 1)
                finally:
                    self._close_runtime(second)

        asyncio.run(run())

    def test_durable_journey_repository_survives_restart(self) -> None:
        async def run() -> None:
            with tempfile.TemporaryDirectory() as tempdir:
                db_path = os.path.join(tempdir, "circulatio.db")
                first = build_hermes_circulatio_runtime(db_path=db_path, llm=FakeCirculatioLlm())
                try:
                    journey = await first.service.create_journey(
                        {
                            "userId": "user_1",
                            "label": "Laundry return",
                            "currentQuestion": "What keeps looping back here?",
                        }
                    )
                    await first.service.set_journey_status(
                        {
                            "userId": "user_1",
                            "journeyId": journey["id"],
                            "status": "paused",
                        }
                    )
                finally:
                    self._close_runtime(first)

                second = build_hermes_circulatio_runtime(db_path=db_path, llm=FakeCirculatioLlm())
                try:
                    reloaded = await second.service.get_journey(
                        {
                            "userId": "user_1",
                            "journeyLabel": "Laundry_Return",
                        }
                    )
                    self.assertEqual(reloaded["id"], journey["id"])
                    self.assertEqual(reloaded["label"], "Laundry return")
                    self.assertEqual(reloaded["status"], "paused")
                    self.assertEqual(
                        reloaded["currentQuestion"],
                        "What keeps looping back here?",
                    )
                finally:
                    self._close_runtime(second)

        asyncio.run(run())

    def test_durable_idempotency_replays_completed_requests_after_restart(self) -> None:
        async def run() -> None:
            with tempfile.TemporaryDirectory() as tempdir:
                db_path = os.path.join(tempdir, "circulatio.db")
                request = {
                    "requestId": "req_1",
                    "idempotencyKey": "idem:interpret:1",
                    "userId": "user_1",
                    "source": {
                        "platform": "cli",
                        "sessionId": "sess_1",
                        "messageId": "msg_1",
                        "profile": "default",
                        "rawCommand": "/circulation reflect snake",
                    },
                    "operation": "circulatio.material.interpret",
                    "payload": {
                        "materialType": "reflection",
                        "text": "I found a snake in the cellar.",
                    },
                }
                first = build_hermes_circulatio_runtime(db_path=db_path, llm=FakeCirculatioLlm())
                try:
                    first_response = await first.bridge.dispatch(request)
                    self.assertEqual(first_response["status"], "ok")
                    self.assertFalse(first_response["replayed"])
                finally:
                    self._close_runtime(first)

                second = build_hermes_circulatio_runtime(db_path=db_path, llm=FakeCirculatioLlm())
                try:
                    replayed_response = await second.bridge.dispatch(request)
                    self.assertEqual(replayed_response["status"], "ok")
                    self.assertTrue(replayed_response["replayed"])
                    self.assertEqual(
                        replayed_response["result"].get("runId"),
                        first_response["result"].get("runId"),
                    )
                finally:
                    self._close_runtime(second)

        asyncio.run(run())

    def test_in_flight_duplicate_dispatch_waits_and_replays_completed_response(self) -> None:
        async def run() -> None:
            with tempfile.TemporaryDirectory() as tempdir:
                db_path = os.path.join(tempdir, "circulatio.db")
                runtime = build_hermes_circulatio_runtime(db_path=db_path, llm=_SlowInterpretLlm())
                first_request = {
                    "requestId": "req_first",
                    "idempotencyKey": "idem:interpret:inflight",
                    "userId": "user_1",
                    "source": {
                        "platform": "cli",
                        "sessionId": "sess_1",
                        "messageId": "msg_1",
                        "profile": "default",
                        "rawCommand": "/circulation reflect snake",
                    },
                    "operation": "circulatio.material.interpret",
                    "payload": {
                        "materialType": "reflection",
                        "text": "I found a snake in the cellar.",
                    },
                }
                second_request = {
                    **first_request,
                    "requestId": "req_second",
                }
                try:
                    first_task = asyncio.create_task(runtime.bridge.dispatch(first_request))
                    await asyncio.sleep(0.01)
                    second_response = await runtime.bridge.dispatch(second_request)
                    first_response = await first_task
                    self.assertEqual(first_response["status"], "ok")
                    self.assertFalse(first_response["replayed"])
                    self.assertEqual(second_response["status"], "ok")
                    self.assertTrue(second_response["replayed"])
                    self.assertEqual(second_response["requestId"], "req_second")
                    self.assertEqual(
                        second_response["result"].get("runId"),
                        first_response["result"].get("runId"),
                    )
                finally:
                    self._close_runtime(runtime)

        asyncio.run(run())

    def test_corrupt_user_bucket_isolated_from_healthy_users(self) -> None:
        async def run() -> None:
            with tempfile.TemporaryDirectory() as tempdir:
                db_path = os.path.join(tempdir, "circulatio.db")
                runtime = build_hermes_circulatio_runtime(db_path=db_path, llm=FakeCirculatioLlm())
                try:
                    healthy_workflow = await runtime.service.create_and_interpret_material(
                        {
                            "userId": "healthy",
                            "materialType": "reflection",
                            "text": "A snake crossed the room.",
                        }
                    )
                    proposal = healthy_workflow["pendingProposals"][0]
                    await runtime.service.approve_proposals(
                        user_id="healthy",
                        run_id=healthy_workflow["run"]["id"],
                        proposal_ids=[proposal["id"]],
                    )
                    corrupt_workflow = await runtime.service.create_and_interpret_material(
                        {
                            "userId": "corrupt",
                            "materialType": "reflection",
                            "text": "A locked chest appeared.",
                        }
                    )
                    self.assertTrue(corrupt_workflow["run"])
                finally:
                    self._close_runtime(runtime)

                with sqlite3.connect(db_path) as connection:
                    connection.execute(
                        "UPDATE circulatio_user_buckets SET payload_json = ? WHERE user_id = ?",
                        ("{not valid json", "corrupt"),
                    )
                    connection.commit()

                reloaded = build_hermes_circulatio_runtime(db_path=db_path, llm=FakeCirculatioLlm())
                try:
                    symbols = await reloaded.repository.list_symbols("healthy")
                    self.assertEqual(len(symbols), 1)
                    self.assertEqual(symbols[0]["canonicalName"], "snake")
                    health = reloaded.repository.storage_health()
                    self.assertIn("corrupt", health["corruptUserIds"])
                    with self.assertRaisesRegex(Exception, "corrupt"):
                        await reloaded.repository.list_symbols("corrupt")
                finally:
                    self._close_runtime(reloaded)

                with sqlite3.connect(db_path) as connection:
                    payload_json = connection.execute(
                        "SELECT payload_json FROM circulatio_user_buckets WHERE user_id = ?",
                        ("corrupt",),
                    ).fetchone()[0]
                self.assertEqual(payload_json, "{not valid json")

        asyncio.run(run())

    def test_persistence_failure_restores_in_memory_bucket(self) -> None:
        async def run() -> None:
            with tempfile.TemporaryDirectory() as tempdir:
                runtime = build_hermes_circulatio_runtime(
                    db_path=os.path.join(tempdir, "circulatio.db"),
                    llm=FakeCirculatioLlm(),
                )
                try:
                    workflow = await runtime.service.create_and_interpret_material(
                        {
                            "userId": "user_rollback",
                            "materialType": "reflection",
                            "text": "A snake crossed the room.",
                        }
                    )
                    before_runs = await runtime.repository.list_interpretation_runs("user_rollback")
                    original_persist = runtime.repository._persist_serialized_user

                    def fail_persist(*args, **kwargs):
                        raise PersistenceError("disk full")

                    runtime.repository._persist_serialized_user = fail_persist
                    with self.assertRaises(PersistenceError):
                        await runtime.service.create_and_interpret_material(
                            {
                                "userId": "user_rollback",
                                "materialType": "reflection",
                                "text": "A locked chest appeared.",
                            }
                        )
                    runtime.repository._persist_serialized_user = original_persist
                    after_runs = await runtime.repository.list_interpretation_runs("user_rollback")
                    self.assertEqual(
                        [item["id"] for item in after_runs],
                        [item["id"] for item in before_runs],
                    )
                    self.assertEqual(workflow["run"]["id"], before_runs[0]["id"])
                finally:
                    self._close_runtime(runtime)

        asyncio.run(run())

    def test_optimistic_revision_conflict_retries_without_overwriting(self) -> None:
        async def run() -> None:
            with tempfile.TemporaryDirectory() as tempdir:
                db_path = os.path.join(tempdir, "circulatio.db")
                first = build_hermes_circulatio_runtime(db_path=db_path, llm=FakeCirculatioLlm())
                second = build_hermes_circulatio_runtime(db_path=db_path, llm=FakeCirculatioLlm())
                verifier = None
                try:
                    first_workflow = await first.service.create_and_interpret_material(
                        {
                            "userId": "shared",
                            "materialType": "reflection",
                            "text": "A snake crossed the room.",
                        }
                    )
                    self.assertTrue(first_workflow["run"])
                    second_workflow = await second.service.create_and_interpret_material(
                        {
                            "userId": "shared",
                            "materialType": "reflection",
                            "text": "A locked chest appeared.",
                        }
                    )
                    self.assertTrue(second_workflow["run"])
                    verifier = build_hermes_circulatio_runtime(
                        db_path=db_path, llm=FakeCirculatioLlm()
                    )
                    healthy = await verifier.repository.list_interpretation_runs("shared")
                    self.assertEqual(len(healthy), 2)
                    self.assertEqual(
                        {first_workflow["run"]["id"], second_workflow["run"]["id"]},
                        {item["id"] for item in healthy},
                    )
                finally:
                    self._close_runtime(first)
                    self._close_runtime(second)
                    if verifier is not None:
                        self._close_runtime(verifier)

        asyncio.run(run())

    def test_stale_started_idempotency_returns_incomplete_error(self) -> None:
        async def run() -> None:
            with tempfile.TemporaryDirectory() as tempdir:
                db_path = os.path.join(tempdir, "circulatio.db")
                runtime = build_hermes_circulatio_runtime(
                    db_path=db_path,
                    llm=FakeCirculatioLlm(),
                    started_ttl_seconds=1,
                )
                request = {
                    "requestId": "req_stale",
                    "idempotencyKey": "idem:stale:1",
                    "userId": "user_stale",
                    "source": {
                        "platform": "cli",
                        "sessionId": "sess_1",
                        "messageId": "msg_1",
                        "profile": "default",
                        "rawCommand": "/circulation reflect snake",
                    },
                    "operation": "circulatio.material.interpret",
                    "payload": {
                        "materialType": "reflection",
                        "text": "I found a snake in the cellar.",
                    },
                }
                try:
                    begin = await runtime.idempotency_store.begin(
                        request["idempotencyKey"], runtime.bridge._request_hash(request)
                    )
                    self.assertEqual(begin["status"], "started")
                    with sqlite3.connect(db_path) as connection:
                        connection.execute(
                            "UPDATE circulatio_idempotency SET updated_at = ? WHERE idempotency_key = ?",
                            ("2000-01-01 00:00:00", request["idempotencyKey"]),
                        )
                        connection.commit()
                    response = await runtime.bridge.dispatch(request)
                    self.assertEqual(response["status"], "retryable_error")
                    self.assertEqual(response["errors"][0]["code"], "idempotency_incomplete")
                    self.assertFalse(response["errors"][0]["retryable"])
                finally:
                    self._close_runtime(runtime)

        asyncio.run(run())

    def test_sqlite_idempotency_begin_is_atomic_across_store_instances(self) -> None:
        async def run() -> None:
            with tempfile.TemporaryDirectory() as tempdir:
                db_path = os.path.join(tempdir, "circulatio.db")
                first = SQLiteIdempotencyStore(db_path)
                second = SQLiteIdempotencyStore(db_path)
                try:
                    results = await asyncio.gather(
                        first.begin("idem:atomic", "hash"),
                        second.begin("idem:atomic", "hash"),
                    )
                finally:
                    first.close()
                    second.close()
                self.assertEqual({result["status"] for result in results}, {"started", "in_flight"})

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
