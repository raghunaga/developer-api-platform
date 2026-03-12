"""
Tests for real-time event streaming infrastructure.

Tests cover:
- Kafka consumer groups
- Event processing pipeline with filtering and aggregation
- Backpressure handling for high-volume streams
"""

import pytest
import time
import uuid
from datetime import datetime, timedelta
from typing import List

from app.services.event_streaming import (
    Event,
    EventType,
    EventSeverity,
    AggregatedMetrics,
    EventFilter,
    SeverityFilter,
    EventTypeFilter,
    DeviceFilter,
    CompositeFilter,
    EventProcessor,
    BackpressureHandler,
    KafkaConsumerGroup,
    EventStreamingManager,
    get_event_streaming_manager,
)


class TestEvent:
    """Tests for Event data structure."""
    
    def test_event_creation(self):
        """Test creating an event."""
        event = Event(
            event_id="evt-001",
            event_type=EventType.DEVICE_METRIC,
            timestamp=datetime.now(),
            device_id="dev-001",
            data={"value": 42.5},
            severity=EventSeverity.LOW,
        )
        
        assert event.event_id == "evt-001"
        assert event.event_type == EventType.DEVICE_METRIC
        assert event.device_id == "dev-001"
        assert event.data["value"] == 42.5
        assert event.severity == EventSeverity.LOW
    
    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        now = datetime.now()
        event = Event(
            event_id="evt-001",
            event_type=EventType.ANOMALY_DETECTED,
            timestamp=now,
            device_id="dev-001",
            data={"anomaly_score": 0.87},
            severity=EventSeverity.HIGH,
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_id"] == "evt-001"
        assert event_dict["event_type"] == "anomaly_detected"
        assert event_dict["device_id"] == "dev-001"
        assert event_dict["data"]["anomaly_score"] == 0.87
        assert event_dict["severity"] == "high"
    
    def test_event_from_dict(self):
        """Test creating event from dictionary."""
        now = datetime.now()
        event_dict = {
            "event_id": "evt-001",
            "event_type": "device_metric",
            "timestamp": now.isoformat(),
            "device_id": "dev-001",
            "data": {"value": 42.5},
            "severity": "medium",
        }
        
        event = Event.from_dict(event_dict)
        
        assert event.event_id == "evt-001"
        assert event.event_type == EventType.DEVICE_METRIC
        assert event.device_id == "dev-001"
        assert event.severity == EventSeverity.MEDIUM


class TestEventFilters:
    """Tests for event filtering."""
    
    def test_severity_filter_matches(self):
        """Test severity filter matching."""
        event_high = Event(
            event_id="evt-001",
            event_type=EventType.ANOMALY_DETECTED,
            timestamp=datetime.now(),
            device_id="dev-001",
            data={},
            severity=EventSeverity.HIGH,
        )
        
        event_low = Event(
            event_id="evt-002",
            event_type=EventType.ANOMALY_DETECTED,
            timestamp=datetime.now(),
            device_id="dev-001",
            data={},
            severity=EventSeverity.LOW,
        )
        
        filter_high = SeverityFilter(EventSeverity.HIGH)
        
        assert filter_high.matches(event_high)
        assert not filter_high.matches(event_low)
    
    def test_event_type_filter(self):
        """Test event type filter."""
        event_metric = Event(
            event_id="evt-001",
            event_type=EventType.DEVICE_METRIC,
            timestamp=datetime.now(),
            device_id="dev-001",
            data={},
        )
        
        event_anomaly = Event(
            event_id="evt-002",
            event_type=EventType.ANOMALY_DETECTED,
            timestamp=datetime.now(),
            device_id="dev-001",
            data={},
        )
        
        filter_metric = EventTypeFilter({EventType.DEVICE_METRIC})
        
        assert filter_metric.matches(event_metric)
        assert not filter_metric.matches(event_anomaly)
    
    def test_device_filter(self):
        """Test device filter."""
        event_dev1 = Event(
            event_id="evt-001",
            event_type=EventType.DEVICE_METRIC,
            timestamp=datetime.now(),
            device_id="dev-001",
            data={},
        )
        
        event_dev2 = Event(
            event_id="evt-002",
            event_type=EventType.DEVICE_METRIC,
            timestamp=datetime.now(),
            device_id="dev-002",
            data={},
        )
        
        filter_dev1 = DeviceFilter({"dev-001"})
        
        assert filter_dev1.matches(event_dev1)
        assert not filter_dev1.matches(event_dev2)
    
    def test_composite_filter(self):
        """Test composite filter with multiple conditions."""
        event = Event(
            event_id="evt-001",
            event_type=EventType.ANOMALY_DETECTED,
            timestamp=datetime.now(),
            device_id="dev-001",
            data={},
            severity=EventSeverity.HIGH,
        )
        
        filters = [
            EventTypeFilter({EventType.ANOMALY_DETECTED}),
            SeverityFilter(EventSeverity.HIGH),
            DeviceFilter({"dev-001"}),
        ]
        
        composite = CompositeFilter(filters)
        
        assert composite.matches(event)
        
        # Change device and test again
        event.device_id = "dev-002"
        assert not composite.matches(event)


class TestEventProcessor:
    """Tests for event processing."""
    
    def test_event_processor_filtering(self):
        """Test event processor applies filters."""
        processor = EventProcessor()
        processor.add_filter(SeverityFilter(EventSeverity.HIGH))
        
        event_high = Event(
            event_id="evt-001",
            event_type=EventType.ANOMALY_DETECTED,
            timestamp=datetime.now(),
            device_id="dev-001",
            data={},
            severity=EventSeverity.HIGH,
        )
        
        event_low = Event(
            event_id="evt-002",
            event_type=EventType.ANOMALY_DETECTED,
            timestamp=datetime.now(),
            device_id="dev-001",
            data={},
            severity=EventSeverity.LOW,
        )
        
        assert processor.process(event_high) is not None
        assert processor.process(event_low) is None
    
    def test_event_processor_aggregation(self):
        """Test event processor aggregates metrics."""
        processor = EventProcessor(window_size_ms=1000)
        
        now = datetime.now()
        events = [
            Event(
                event_id=f"evt-{i:03d}",
                event_type=EventType.DEVICE_METRIC,
                timestamp=now + timedelta(milliseconds=i*100),
                device_id="dev-001",
                data={"value": 10 + i},
            )
            for i in range(5)
        ]
        
        aggregated = None
        for event in events:
            aggregated = processor.aggregate_metrics(event)
        
        assert aggregated is not None
        assert aggregated.device_id == "dev-001"
        assert aggregated.metric_count == 5
        assert aggregated.min_value == 10
        assert aggregated.max_value == 14
        assert aggregated.avg_value == 12.0


class TestBackpressureHandler:
    """Tests for backpressure handling."""
    
    def test_backpressure_queue_size_limit(self):
        """Test backpressure applies when queue is full."""
        handler = BackpressureHandler(max_queue_size=3)
        
        events = [
            Event(
                event_id=f"evt-{i:03d}",
                event_type=EventType.DEVICE_METRIC,
                timestamp=datetime.now(),
                device_id="dev-001",
                data={"value": i},
            )
            for i in range(5)
        ]
        
        # Enqueue first 3 events
        for i in range(3):
            assert handler.enqueue(events[i])
        
        # 4th event should be rejected due to backpressure
        assert not handler.enqueue(events[3])
        
        # Queue size should be 3
        assert handler.queue_size() == 3
    
    def test_backpressure_rate_limiting(self):
        """Test backpressure rate limiting."""
        handler = BackpressureHandler(max_queue_size=100, max_processing_rate=5)
        
        # Enqueue 10 events
        for i in range(10):
            assert handler.enqueue(Event(
                event_id=f"evt-{i:03d}",
                event_type=EventType.DEVICE_METRIC,
                timestamp=datetime.now(),
                device_id="dev-001",
                data={"value": i},
            ))
        
        # Dequeue 5 events (should succeed)
        for i in range(5):
            event = handler.dequeue()
            assert event is not None
        
        # 6th dequeue should fail due to rate limit
        assert handler.dequeue() is None
        
        # After 1 second, should be able to dequeue again
        time.sleep(1.1)
        event = handler.dequeue()
        assert event is not None
    
    def test_backpressure_can_accept(self):
        """Test can_accept method."""
        handler = BackpressureHandler(max_queue_size=2)
        
        assert handler.can_accept()
        
        handler.enqueue(Event(
            event_id="evt-001",
            event_type=EventType.DEVICE_METRIC,
            timestamp=datetime.now(),
            device_id="dev-001",
            data={},
        ))
        
        assert handler.can_accept()
        
        handler.enqueue(Event(
            event_id="evt-002",
            event_type=EventType.DEVICE_METRIC,
            timestamp=datetime.now(),
            device_id="dev-001",
            data={},
        ))
        
        assert not handler.can_accept()


class TestKafkaConsumerGroup:
    """Tests for Kafka consumer group."""
    
    def test_consumer_group_creation(self):
        """Test creating a consumer group."""
        group = KafkaConsumerGroup(
            group_id="test-group",
            topics=["device-metrics", "anomalies"],
        )
        
        assert group.group_id == "test-group"
        assert group.topics == ["device-metrics", "anomalies"]
        assert not group.is_running
    
    def test_consumer_group_add_filter(self):
        """Test adding filters to consumer group."""
        group = KafkaConsumerGroup(
            group_id="test-group",
            topics=["device-metrics"],
        )
        
        group.add_filter(SeverityFilter(EventSeverity.HIGH))
        
        assert len(group.event_processor.filters) == 1
    
    def test_consumer_group_subscribe(self):
        """Test subscribing to consumer group."""
        group = KafkaConsumerGroup(
            group_id="test-group",
            topics=["device-metrics"],
        )
        
        received_events = []
        
        def callback(event: Event):
            received_events.append(event)
        
        group.subscribe(callback)
        
        assert len(group.callbacks) == 1
    
    def test_consumer_group_push_event(self):
        """Test pushing events to consumer group."""
        group = KafkaConsumerGroup(
            group_id="test-group",
            topics=["device-metrics"],
        )
        
        event = Event(
            event_id="evt-001",
            event_type=EventType.DEVICE_METRIC,
            timestamp=datetime.now(),
            device_id="dev-001",
            data={"value": 42.5},
        )
        
        assert group.push_event(event)
        assert group.get_queue_size() == 1
    
    def test_consumer_group_start_stop(self):
        """Test starting and stopping consumer group."""
        group = KafkaConsumerGroup(
            group_id="test-group",
            topics=["device-metrics"],
        )
        
        assert not group.is_running
        
        group.start()
        assert group.is_running
        
        group.stop()
        assert not group.is_running
    
    def test_consumer_group_event_processing(self):
        """Test consumer group processes events."""
        group = KafkaConsumerGroup(
            group_id="test-group",
            topics=["device-metrics"],
            max_queue_size=100,
            max_processing_rate=100,
        )
        
        received_events = []
        
        def callback(event: Event):
            received_events.append(event)
        
        group.subscribe(callback)
        group.add_filter(SeverityFilter(EventSeverity.HIGH))
        
        group.start()
        
        # Push high severity event
        event_high = Event(
            event_id="evt-001",
            event_type=EventType.ANOMALY_DETECTED,
            timestamp=datetime.now(),
            device_id="dev-001",
            data={},
            severity=EventSeverity.HIGH,
        )
        
        # Push low severity event
        event_low = Event(
            event_id="evt-002",
            event_type=EventType.ANOMALY_DETECTED,
            timestamp=datetime.now(),
            device_id="dev-001",
            data={},
            severity=EventSeverity.LOW,
        )
        
        group.push_event(event_high)
        group.push_event(event_low)
        
        # Wait for processing
        time.sleep(0.5)
        
        group.stop()
        
        # Only high severity event should be received
        assert len(received_events) == 1
        assert received_events[0].event_id == "evt-001"
    
    def test_consumer_group_get_status(self):
        """Test getting consumer group status."""
        group = KafkaConsumerGroup(
            group_id="test-group",
            topics=["device-metrics"],
            max_queue_size=1000,
            max_processing_rate=500,
        )
        
        status = group.get_status()
        
        assert status["group_id"] == "test-group"
        assert status["topics"] == ["device-metrics"]
        assert status["is_running"] is False
        assert status["queue_size"] == 0
        assert status["max_queue_size"] == 1000
        assert status["max_processing_rate"] == 500


class TestEventStreamingManager:
    """Tests for event streaming manager."""
    
    def test_manager_create_consumer_group(self):
        """Test creating consumer group through manager."""
        manager = EventStreamingManager()
        
        group = manager.create_consumer_group(
            group_id="test-group",
            topics=["device-metrics"],
        )
        
        assert group.group_id == "test-group"
        assert manager.get_consumer_group("test-group") is group
    
    def test_manager_duplicate_group_error(self):
        """Test error when creating duplicate consumer group."""
        manager = EventStreamingManager()
        
        manager.create_consumer_group(
            group_id="test-group",
            topics=["device-metrics"],
        )
        
        with pytest.raises(ValueError):
            manager.create_consumer_group(
                group_id="test-group",
                topics=["anomalies"],
            )
    
    def test_manager_start_stop_all(self):
        """Test starting and stopping all consumer groups."""
        manager = EventStreamingManager()
        
        group1 = manager.create_consumer_group(
            group_id="group-1",
            topics=["device-metrics"],
        )
        
        group2 = manager.create_consumer_group(
            group_id="group-2",
            topics=["anomalies"],
        )
        
        manager.start_all()
        
        assert group1.is_running
        assert group2.is_running
        
        manager.stop_all()
        
        assert not group1.is_running
        assert not group2.is_running
    
    def test_manager_get_all_status(self):
        """Test getting status of all consumer groups."""
        manager = EventStreamingManager()
        
        manager.create_consumer_group(
            group_id="group-1",
            topics=["device-metrics"],
        )
        
        manager.create_consumer_group(
            group_id="group-2",
            topics=["anomalies"],
        )
        
        status = manager.get_all_status()
        
        assert "group-1" in status
        assert "group-2" in status
        assert status["group-1"]["group_id"] == "group-1"
        assert status["group-2"]["group_id"] == "group-2"
    
    def test_global_manager_singleton(self):
        """Test global event streaming manager is singleton."""
        manager1 = get_event_streaming_manager()
        manager2 = get_event_streaming_manager()
        
        assert manager1 is manager2


class TestEventStreamingIntegration:
    """Integration tests for event streaming."""
    
    def test_high_volume_event_streaming(self):
        """Test handling high-volume event streams."""
        manager = EventStreamingManager()
        
        group = manager.create_consumer_group(
            group_id="high-volume",
            topics=["device-metrics"],
            max_queue_size=1000,
            max_processing_rate=500,
        )
        
        received_events = []
        
        def callback(event: Event):
            received_events.append(event)
        
        group.subscribe(callback)
        group.start()
        
        # Push 100 events
        for i in range(100):
            event = Event(
                event_id=f"evt-{i:03d}",
                event_type=EventType.DEVICE_METRIC,
                timestamp=datetime.now(),
                device_id=f"dev-{i % 10:03d}",
                data={"value": i},
            )
            group.push_event(event)
        
        # Wait for processing
        time.sleep(1)
        
        group.stop()
        
        # All events should be processed
        assert len(received_events) == 100
    
    def test_multi_topic_streaming(self):
        """Test streaming from multiple topics."""
        manager = EventStreamingManager()
        
        metrics_group = manager.create_consumer_group(
            group_id="metrics",
            topics=["device-metrics"],
        )
        
        anomaly_group = manager.create_consumer_group(
            group_id="anomalies",
            topics=["anomalies"],
        )
        
        metrics_received = []
        anomalies_received = []
        
        metrics_group.subscribe(lambda e: metrics_received.append(e))
        anomaly_group.subscribe(lambda e: anomalies_received.append(e))
        
        metrics_group.start()
        anomaly_group.start()
        
        # Push metric event
        metric_event = Event(
            event_id="evt-001",
            event_type=EventType.DEVICE_METRIC,
            timestamp=datetime.now(),
            device_id="dev-001",
            data={"value": 42.5},
        )
        
        # Push anomaly event
        anomaly_event = Event(
            event_id="evt-002",
            event_type=EventType.ANOMALY_DETECTED,
            timestamp=datetime.now(),
            device_id="dev-001",
            data={"anomaly_score": 0.87},
            severity=EventSeverity.HIGH,
        )
        
        metrics_group.push_event(metric_event)
        anomaly_group.push_event(anomaly_event)
        
        # Wait for processing
        time.sleep(0.5)
        
        metrics_group.stop()
        anomaly_group.stop()
        
        assert len(metrics_received) == 1
        assert len(anomalies_received) == 1
