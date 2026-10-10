"""Offline regression tests: all network transports are replaced or blocked."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import requests
import ai_analyzer as ai
import send_telegram as telegram
import scoring
from vacancy_state import load_sent_ids


def vacancy(identifier=1, **changes):
    return dict({"id": str(identifier), "title": "Technical Writer", "category": "HOT",
                 "score": 60, "description": "Обязанности: писать документацию. Требования: SQL, API. " * 4,
                 "url": "https://hh.ru/vacancy/1", "remote": True}, **changes)


def result(**changes):
    return dict({"ai_score": 85, "ai_recommendation": "APPLY", "ai_strengths": ["Опыт документации", "Анализ проблем"],
                 "ai_gaps": ["Уровень SQL нужно уточнить"], "ai_reason": "Совпадают задачи; зарплата неизвестна."}, **changes)


def response(**changes):
    return SimpleNamespace(status="completed", output_text=json.dumps(result(**changes)),
                           usage=SimpleNamespace(input_tokens=100, output_tokens=50))


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"AI_ENABLED": "true", "OPENAI_API_KEY": "offline-placeholder",
                                                   "AI_MAX_VACANCIES": "20", "OPENAI_MODEL": "gpt-5-nano"}, clear=True)
        self.environment.start()
        self.network = patch("requests.sessions.Session.request", side_effect=AssertionError("Live HTTP forbidden"))
        self.network.start()
        self.addCleanup(self.environment.stop)
        self.addCleanup(self.network.stop)
        self.client = Mock()
        self.client.responses.create.return_value = response()
        self.factory = Mock(return_value=self.client)

    def analyze(self, vacancies, sent=()):
        return ai.analyze_vacancies(vacancies, set(sent), self.factory, {"skills": ["Документация"]})

    def test_success_schema_model_usage_and_original_score(self):
        rows, stats = self.analyze([vacancy()])
        self.assertEqual(rows[0]["score"], 60)
        self.assertEqual(rows[0]["ai_score"], 85)
        self.assertEqual(rows[0]["ai_status"], "success")
        self.assertEqual(stats, dict(requests=1, errors=0, input_tokens=100, output_tokens=50))
        self.factory.assert_called_once_with(timeout=45.0, max_retries=0)
        args = self.client.responses.create.call_args.kwargs
        self.assertEqual(args["model"], "gpt-5-nano")
        self.assertTrue(args["text"]["format"]["strict"])
        self.assertFalse(args["store"])

    def test_disabled_ignores_stale_ai_and_never_creates_client(self):
        os.environ["AI_ENABLED"] = "false"
        rows, stats = self.analyze([vacancy(ai_status="success", ai_recommendation="SKIP")])
        self.factory.assert_not_called()
        self.assertEqual(stats["requests"], 0)
        self.assertEqual(rows[0]["ai_status"], "disabled")
        self.assertEqual(len(telegram.select_vacancies(rows, set(), False)), 1)

    def test_no_key_falls_back(self):
        del os.environ["OPENAI_API_KEY"]
        rows, stats = self.analyze([vacancy()])
        self.factory.assert_not_called()
        self.assertEqual(rows[0]["ai_status"], "unavailable")
        self.assertEqual(stats["requests"], 0)
        self.assertEqual(len(telegram.select_vacancies(rows, set(), True)), 1)

    def test_excludes_sent_duplicates_and_low_categories(self):
        rows, stats = self.analyze([vacancy(1), vacancy(2), vacancy(2), vacancy(3, category="MAYBE"), vacancy(4, category="SKIP")], {"1"})
        self.assertEqual(stats["requests"], 1)
        self.assertEqual(len(telegram.select_vacancies(rows, {"1"}, True)), 1)

    def test_empty_incomplete_descriptions_skip_without_requests(self):
        for description in (None, "", "  ", "SQL", [], 100):
            with self.subTest(description=description):
                rows, stats = self.analyze([vacancy(description=description)])
                self.assertEqual(rows[0]["ai_status"], "insufficient_data")
                self.assertEqual(stats["requests"], 0)
        self.factory.assert_not_called()

    def test_limit_and_hard_cap(self):
        for value, expected in (("2", 2), ("100", 20), ("-1", 0), ("0", 0), ("bad", 0)):
            with self.subTest(limit=value):
                os.environ["AI_MAX_VACANCIES"] = value
                rows, stats = self.analyze([vacancy(i) for i in range(30)])
                self.assertEqual(stats["requests"], expected)
                self.assertEqual(sum(v["ai_status"] == "success" for v in rows), expected)

    def test_api_error_stops_requests_and_does_not_log_secret(self):
        self.client.responses.create.side_effect = RuntimeError("secret-token")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            rows, stats = self.analyze([vacancy(i) for i in range(4)])
        self.assertNotIn("secret-token", output.getvalue())
        self.assertEqual(stats["requests"], 1)
        self.assertEqual(stats["errors"], 1)
        self.assertEqual(rows[1]["ai_status"], "unavailable")
        self.assertEqual(len(telegram.select_vacancies(rows, set(), True)), 4)

    def test_invalid_responses_and_refusal_fall_back(self):
        invalid = [response(ai_score=101), response(ai_score=True), response(ai_recommendation="UNKNOWN"),
                   response(ai_strengths="SQL"), response(ai_reason=""),
                   SimpleNamespace(status="incomplete", output_text="", usage=None),
                   SimpleNamespace(status="completed", output_text="not JSON", usage=None)]
        for value in invalid:
            with self.subTest(value=value):
                self.client.responses.create.return_value = value
                rows, stats = self.analyze([vacancy()])
                self.assertEqual(rows[0]["ai_status"], "error")
                self.assertEqual(stats["errors"], 1)

    def test_missing_or_invalid_profile_fallback(self):
        with patch.object(ai, "PROFILE_FILE", Path("does-not-exist.json")):
            rows, stats = ai.analyze_vacancies([vacancy()], set(), self.factory)
        self.factory.assert_not_called()
        self.assertEqual(rows[0]["ai_status"], "unavailable")

    def test_ranking_skip_and_telegram_limit(self):
        rows = [vacancy(1, ai_status="success", **result(ai_recommendation="CONSIDER", ai_score=99)),
                vacancy(2, ai_status="success", **result(ai_score=60)),
                vacancy(3, ai_status="success", **result(ai_score=90)),
                vacancy(4, ai_status="success", **result(ai_recommendation="SKIP")), vacancy(5)]
        self.assertEqual([v["id"] for v in telegram.select_vacancies(rows, set(), True)], ["3", "2", "1", "5"])
        self.assertEqual(len(telegram.select_vacancies([vacancy(i) for i in range(40)], set(), False)), 20)

    def test_message_shows_ai_and_is_bounded(self):
        row = vacancy(ai_status="success", **result())
        text = telegram.format_message(row, True)
        for word in ("85/100", "откликаться", "Уровень SQL", "60 баллов", "https://hh.ru"):
            self.assertIn(word, text)
        self.assertNotIn("85/100", telegram.format_message(row, False))
        row.update(result(ai_strengths=["x" * 300] * 3, ai_gaps=["x" * 300] * 3, ai_reason="x" * 800))
        row.update(title="x" * 1000, company="x" * 1000, location="x" * 1000, salary_text="x" * 1000, url="x" * 1000)
        self.assertLess(len(telegram.format_message(row, True)), 4096)

    def test_history_only_after_success_and_no_repeat(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            history, data = Path(directory) / "sent.json", Path(directory) / "scored.json"
            data.write_text(json.dumps([vacancy(1), vacancy(2), vacancy(2)]), encoding="utf-8")
            history.write_text('[1]', encoding="utf-8")
            os.environ.update(AI_ENABLED="false", TELEGRAM_BOT_TOKEN="offline", TELEGRAM_CHAT_ID="offline")
            with patch.object(telegram, "INPUT_FILE", str(data)), patch.object(telegram, "SENT_FILE", str(history)):
                with patch.object(telegram, "send_message", side_effect=[None, requests.RequestException("secret")]):
                    telegram.main()
                self.assertEqual(load_sent_ids(history), {"1"})
                with patch.object(telegram, "send_message", return_value=None) as send:
                    telegram.main()
                    self.assertEqual(send.call_count, 2)
                self.assertEqual(load_sent_ids(history), {"1", "2"})
                with patch.object(telegram, "send_message", return_value=None) as send:
                    telegram.main()
                    self.assertEqual(send.call_count, 1)  # Empty-results notification only.

    def test_corrupted_history_fails_closed(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            path = Path(directory) / "sent.json"
            for contents in ('{"ids": []}', '[null]', 'broken'):
                path.write_text(contents, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_sent_ids(path)

    def test_telegram_requires_success_payload(self):
        os.environ.update(TELEGRAM_BOT_TOKEN="offline", TELEGRAM_CHAT_ID="offline")
        with patch("requests.post") as post:
            post.return_value.json.return_value = {"ok": False}
            with self.assertRaises(requests.RequestException):
                telegram.send_message("offline")
            post.return_value.json.return_value = {"ok": True}
            telegram.send_message("offline")

    def test_description_truncation_and_model_override(self):
        os.environ["OPENAI_MODEL"] = "configured-model"
        self.analyze([vacancy(description="x" * 20000)])
        kwargs = self.client.responses.create.call_args.kwargs
        payload = json.loads(kwargs["input"])["vacancy"]
        self.assertEqual(len(payload["description"]), 12000)
        self.assertTrue(payload["description_truncated"])
        self.assertEqual(kwargs["model"], "configured-model")

    def test_rule_scoring_json_flows_into_ai(self):
        row = vacancy(skills=["SQL"], salary_from=120000, currency="RUB")
        row.update(scoring.score_vacancy(row))
        original = row["score"]
        rows, _ = self.analyze(json.loads(json.dumps([row])))
        self.assertEqual(rows[0]["score"], original)
        self.assertEqual(rows[0]["ai_status"], "success")

    def test_real_sdk_with_offline_transport(self):
        import httpx
        from openai import OpenAI
        seen = []

        def handle(request):
            seen.append(json.loads(request.content))
            return httpx.Response(200, json={
                "id": "resp_offline", "object": "response", "created_at": 0,
                "model": "gpt-5-nano", "status": "completed",
                "output": [{"type": "message", "id": "msg_offline", "role": "assistant", "status": "completed",
                            "content": [{"type": "output_text", "text": json.dumps(result()), "annotations": []}]}],
                "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            })

        def factory(**kwargs):
            return OpenAI(api_key="offline", http_client=httpx.Client(transport=httpx.MockTransport(handle)), **kwargs)

        rows, stats = ai.analyze_vacancies([vacancy()], set(), factory, {"skills": ["SQL"]})
        self.assertEqual(rows[0]["ai_status"], "success")
        self.assertEqual(stats["input_tokens"], 100)
        self.assertEqual(seen[0]["text"]["format"]["type"], "json_schema")

    def test_ai_stage_writes_json_without_key_or_when_disabled(self):
        del os.environ["OPENAI_API_KEY"]
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            source, output = Path(directory) / "scored.json", Path(directory) / "ai.json"
            source.write_text(json.dumps([vacancy()]), encoding="utf-8")
            for enabled, expected in (("true", "unavailable"), ("false", "disabled")):
                os.environ["AI_ENABLED"] = enabled
                with patch.object(ai, "INPUT_FILE", str(source)), patch.object(ai, "OUTPUT_FILE", str(output)), patch.object(ai, "load_sent_ids", return_value=set()):
                    ai.main()
                rows = json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual(rows[0]["ai_status"], expected)
                self.assertEqual(rows[0]["score"], 60)
                self.assertEqual(len(telegram.select_vacancies(rows, set(), enabled == "true")), 1)

    def test_validation_requires_exact_fields(self):
        missing = result()
        del missing["ai_gaps"]
        for invalid in (missing, result(extra="field"), result(ai_gaps=["x"] * 4)):
            with self.assertRaises(ValueError):
                ai.validate_result(invalid)


if __name__ == "__main__":
    unittest.main()
