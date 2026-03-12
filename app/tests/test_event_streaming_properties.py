"""
Property-based tests for real-time event streaming infrastructure.

**Validates: Requirements 4, 12, 17**

These tests verify correctness properties of the event streaming system:
- Events are processed in order
- Backpressure prevents queue overflow
- Filtering is consistent
- Aggregation produces correct statistics
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, HealthCheck
from hypothesis.strategies import composite

from app.services.event_streaming import (
    Event,
    EventType,
    EventSeverity,
    EventProcessor,
    BackpressureHandler,
    KafkaConsumerGroup,
    SeverityFilter,
    EventTypeFilter,
    DeviceFilter,
)


# Custom strategies for generating test data

@composite
def event_types(draw):
    """Generate random event types."""
    return draw(st.sampled_from(list(EventType)))


@composite
def event_severities(draw):
    """Generate random event severities."""
    return draw(st.sampled_from(list(EventSeverity)))


@composite
def events(draw, event_type=None, severity=None):
    """Generate random events."""
    return Event(
        event_id=draw(st.uuids()).hex,
        event_type=event_type or draw(event_types()),
        timestamp=draw(st.datetimes(min_value=datetime(2000, 1, 1))),
        device_id=draw(st.text(alphabet="0123456789", min_size=1, max_size=10)),
        data=draw(st.dictionaries(
            keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=10),
            values=st.floats(allow_nan=False, allow_infinity=False),
            max_size=5,
        )),
        severity=severity or draw(st.one_of(st.none(), event_severities())),
    )


class TestEventStreamingProperties:
    """Property-based tests for event streaming."""
    
    @given(st.lists(events(), min_size=1, max_size=100))
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_event_processor_preserves_event_data(self, event_list):
        """
        **Property: Event Data Preservation**
        
        For any list of events, the event processor should preserve all event data
        when no filters are applied.
        """
        processor = EventProcessor()
        
        processed_events = []
        for event in event_list:
            processed = processor.process(event)
            if processed:
                processed_events.append(processed)
        
        # All events should pass through without filters
        assert len(processed_events) == len(event_list)
        
        # Event data should be identical
        for original, processed in zip(event_list, processed_events):
            assert original.event_id == processed.event_id
            assert original.event_type == processed.event_type
            assert original.device_id == processed.device_id
            assert original.data == processed.data
    
    @given(st.lists(events(severity=EventSeverity.HIGH), min_size=1, max_size=50))
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_severity_filter_consistency(self, event_list):
        """
        **Property: Severity Filter Consistency**
        
        For any list of high-severity events, a high-severity filter should
        accept all events consistently.
        """
        processor = EventProcessor()
        processor.add_filter(SeverityFilter(EventSeverity.HIGH))
        
        # Process events multiple times
        results1 = [processor.process(e) for e in event_list]
        results2 = [processor.process(e) for e in event_list]
        
        # Results should be identical
        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert (r1 is None) == (r2 is None)
            if r1 is not None:
                assert r1.event_id == r2.event_id
    
    @given(st.lists(events(), min_size=1, max_size=100))
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_backpressure_queue_never_exceeds_limit(self, event_list):
        """
        **Property: Backpressure Queue Limit**
        
        For any list of events, the backpressure handler should never allow
        the queue to exceed the configured maximum size.
        """
        max_size = 10
        handler = BackpressureHandler(max_queue_size=max_size)
        
        accepted_count = 0
        for event in event_list:
            if handler.enqueue(event):
                accepted_count += 1
        
        # Queue size should never exceed max
        assert handler.queue_size() <= max_size
        
        # If we accepted events, queue should have them
        if accepted_count > 0:
            assert handler.queue_size() > 0
    
    @given(st.lists(events(), min_size=1, max_size=50))
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_backpressure_dequeue_order(self, event_list):
        """
        **Property: Backpressure FIFO Order**
        
        For any list of events, the backpressure handler should dequeue
        events in FIFO order.
        """
        handler = BackpressureHandler(max_queue_size=len(event_list) + 10)
        
        # Enqueue all events
        for event in event_list:
            handler.enqueue(event)
        
        # Dequeue and verify order
        dequeued = []
        while True:
            event = handler.dequeue()
            if event is None:
                break
            dequeued.append(event)
        
        # Should dequeue in same order
        assert len(dequeued) == len(event_list)
        for original, dequeued_event in zip(event_list, dequeued):
            assert original.event_id == dequeued_event.event_id
    
    @given(
        st.lists(events(event_type=EventType.DEVICE_METRIC), min_size=1, max_size=50),
        st.integers(min_value=100, max_value=5000),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_metric_aggregation_statistics(self, event_list, window_size_ms):
        """
        **Property: Metric Aggregation Correctness**
        
        For any list of metric events, the aggregation should produce
        correct min, max, and average values.
        """
        processor = EventProcessor(window_size_ms=window_size_ms)
        
        # Aggregate all events
        aggregated = None
        for event in event_list:
            aggregated = processor.aggregate_metrics(event)
        
        if aggregated is not None:
            # Extract values from events
            values = [e.data.get("value", 0) for e in event_list if "value" in e.data]
            
            if values:
                # Verify statistics
                assert aggregated.min_value == min(values)
                assert aggregated.max_value == max(values)
                assert abs(aggregated.avg_value - (sum(values) / len(values))) < 0.001
                assert aggregated.metric_count == len(event_list)
    
    @given(st.lists(events(), min_size=1, max_size=100))
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_event_type_filter_idempotence(self, event_list):
        """
        **Property: Event Type Filter Idempotence**
        
        For any list of events and event type filter, applying the filter
        multiple times should produce the same result.
        """
        event_types_to_filter = {EventType.DEVICE_METRIC, EventType.ANOMALY_DETECTED}
        
        processor1 = EventProcessor()
        processor1.add_filter(EventTypeFilter(event_types_to_filter))
        
        processor2 = EventProcessor()
        processor2.add_filter(EventTypeFilter(event_types_to_filter))
        
        # Process with both processors
        results1 = [processor1.process(e) for e in event_list]
        results2 = [processor2.process(e) for e in event_list]
        
        # Results should be identical
        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert (r1 is None) == (r2 is None)
            if r1 is not None:
                assert r1.event_id == r2.event_id
    
    @given(st.lists(events(), min_size=1, max_size=100))
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_device_filter_correctness(self, event_list):
        """
        **Property: Device Filter Correctness**
        
        For any list of events and device filter, only events from
        specified devices should pass through.
        """
        if not event_list:
            return
        
        # Get unique device IDs from events
        device_ids = {e.device_id for e in event_list}
        
        # Filter for first device only
        first_device = next(iter(device_ids))
        processor = EventProcessor()
        processor.add_filter(DeviceFilter({first_device}))
        
        # Process all events
        processed = [processor.process(e) for e in event_list]
        
        # All processed events should be from first device
        for event in processed:
            if event is not None:
                assert event.device_id == first_device
    
    @given(st.lists(events(), min_size=1, max_size=100))
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_consumer_group_event_ordering(self, event_list):
        """
        **Property: Consumer Group Event Ordering**
        
        For any list of events pushed to a consumer group, events should
        be processed in the order they were pushed.
        """
        group = KafkaConsumerGroup(
            group_id="test-group",
            topics=["test"],
            max_queue_size=len(event_list) + 10,
            max_processing_rate=1000,
        )
        
        received_events = []
        
        def callback(event: Event):
            received_events.append(event)
        
        group.subscribe(callback)
        group.start()
        
        # Push all events
        for event in event_list:
            group.push_event(event)
        
        # Wait for processing
        import time
        time.sleep(0.5)
        
        group.stop()
        
        # Verify order
        assert len(received_events) == len(event_list)
        for original, received in zip(event_list, received_events):
            assert original.event_id == received.event_id
    
    @given(st.integers(min_value=1, max_value=100))
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_backpressure_rate_limiting_enforcement(self, rate_limit):
        """
        **Property: Backpressure Rate Limiting**
        
        For any rate limit, the backpressure handler should not allow
        more than the specified number of events per second.
        """
        handler = BackpressureHandler(max_queue_size=1000, max_processing_rate=rate_limit)
        
        # Enqueue many events
        for i in range(rate_limit * 2):
            event = Event(
                event_id=f"evt-{i:04d}",
                event_type=EventType.DEVICE_METRIC,
                timestamp=datetime.now(),
                device_id="dev-001",
                data={"value": i},
            )
            handler.enqueue(event)
        
        # Dequeue within first second
        dequeued_count = 0
        while True:
            event = handler.dequeue()
            if event is None:
                break
            dequeued_count += 1
        
        # Should not exceed rate limit
        assert dequeued_count <= rate_limit
    
    @given(st.lists(events(), min_size=1, max_size=100))
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_event_serialization_roundtrip(self, event_list):
        """
        **Property: Event Serialization Roundtrip**
        
        For any list of events, serializing to dict and deserializing
        should produce identical events.
        """
        for original_event in event_list:
            # Serialize
            event_dict = original_event.to_dict()
            
            # Deserialize
            restored_event = Event.from_dict(event_dict)
            
            # Verify identity
            assert original_event.event_id == restored_event.event_id
            assert original_event.event_type == restored_event.event_type
            assert original_event.device_id == restored_event.device_id
            assert original_event.data == restored_event.data
            assert original_event.severity == restored_event.severity
