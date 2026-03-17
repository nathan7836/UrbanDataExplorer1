"""Tests Kafka streaming (mock — pas de broker requis en CI)."""

from unittest.mock import MagicMock, patch

from ude_platform.kafka_streaming import publish_kafka_event, streaming_catalogue


@patch("ude_platform.kafka_streaming._producer")
def test_publish_kafka_event_ok(mock_producer_fn):
    producer = MagicMock()
    future = MagicMock()
    producer.send.return_value = future
    mock_producer_fn.return_value = producer

    assert publish_kafka_event("pipeline.completed", {"n": 20}) is True
    producer.send.assert_called_once()
    future.get.assert_called_once()


@patch("ude_platform.kafka_streaming.check_kafka", return_value=False)
def test_streaming_catalogue(mock_check):
    cat = streaming_catalogue()
    assert cat["kafka"]["topic"] == "ude.pipeline.events"
    assert "redis_streams" in cat["comparaison"]
    assert cat["kafka"]["disponible"] is False
