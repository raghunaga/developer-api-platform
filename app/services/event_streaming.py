"""
Real-time event streaming infrastructure for device metrics and anomalies.

This module provides:
- Kafka consumer for device metrics and anomaly streams
- Event processing pipeline with filtering and aggregation
- Backpressure handling for high-volume streams
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict, deque
from threading import Lock, Thread, Event as ThreadingEvent

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events that can be streamed."""
    DEVICE_METRIC = "device_metric"
    ANOMALY_DETECTED = "anomaly_detected"
    DEVICE_STATUS_CHANGE = "device_status_change"
    PREDICTION_UPDATE = "prediction_update"


class EventSeverity(Enum):
    """Severity levels for events."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Event:
    """Base event structure for streaming."""
    event_id: str
    event_type: EventType
    timestamp: datetime
    device_id: str
    data: Dict[str, Any]
    severity: Optional[EventSeverity] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "device_id": self.device_id,
            "data": self.data,
            "severity": self.severity.value if self.severity else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary."""
        return cls(
            event_id=data["event_id"],
            event_type=EventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            device_id=data["device_id"],
            data=data["data"],
            severity=EventSeverity(data["severity"]) if data.get("severity") else None,
        )


@dataclass
class AggregatedMetrics:
    """Aggregated metrics for a device over a time window."""
    device_id: str
    window_start: datetime
    window_end: datetime
    metric_count: int
    avg_value: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    anomaly_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class EventFilter(ABC):
    """Abstract base class for event filters."""
    
    @abstractmethod
    def matches(self, event: Event) -> bool:
        """Check if event matches filter criteria."""
        pass


class SeverityFilter(EventFilter):
    """Filter events by severity level."""
    
    def __init__(self, min_severity: EventSeverity):
        self.min_severity = min_severity
        self.severity_order = {
            EventSeverity.LOW: 0,
            EventSeverity.MEDIUM: 1,
            EventSeverity.HIGH: 2,
            EventSeverity.CRITICAL: 3,
        }
    
    def matches(self, event: Event) -> bool:
        """Check if event severity meets minimum threshold."""
        if event.severity is None:
            return False
        return self.severity_order[event.severity] >= self.severity_order[self.min_severity]


class EventTypeFilter(EventFilter):
    """Filter events by type."""
    
    def __init__(self, event_types: Set[EventType]):
        self.event_types = event_types
    
    def matches(self, event: Event) -> bool:
        """Check if event type is in allowed set."""
        return event.event_type in self.event_types


class DeviceFilter(EventFilter):
    """Filter events by device ID."""
    
    def __init__(self, device_ids: Set[str]):
        self.device_ids = device_ids
    
    def matches(self, event: Event) -> bool:
        """Check if event device is in allowed set."""
        return event.device_id in self.device_ids


class CompositeFilter(EventFilter):
    """Combine multiple filters with AND logic."""
    
    def __init__(self, filters: List[EventFilter]):
        self.filters = filters
    
    def matches(self, event: Event) -> bool:
        """Check if event matches all filters."""
        return all(f.matches(event) for f in self.filters)


class EventProcessor:
    """Process events with filtering and aggregation."""
    
    def __init__(self, window_size_ms: int = 1000):
        """
        Initialize event processor.
        
        Args:
            window_size_ms: Time window for aggregation in milliseconds
        """
        self.window_size_ms = window_size_ms
        self.filters: List[EventFilter] = []
        self.aggregation_windows: Dict[str, deque] = defaultdict(deque)
        self.lock = Lock()
    
    def add_filter(self, event_filter: EventFilter) -> None:
        """Add a filter to the processing pipeline."""
        self.filters.append(event_filter)
    
    def process(self, event: Event) -> Optional[Event]:
        """
        Process event through filters.
        
        Args:
            event: Event to process
            
        Returns:
            Event if it passes all filters, None otherwise
        """
        for event_filter in self.filters:
            if not event_filter.matches(event):
                return None
        return event
    
    def aggregate_metrics(self, event: Event) -> Optional[AggregatedMetrics]:
        """
        Aggregate metrics for a device over time window.
        
        Args:
            event: Event containing metric data
            
        Returns:
            Aggregated metrics if window is complete, None otherwise
        """
        if event.event_type != EventType.DEVICE_METRIC:
            return None
        
        with self.lock:
            device_id = event.device_id
            window_key = (device_id, event.timestamp.timestamp() // (self.window_size_ms / 1000))
            
            self.aggregation_windows[device_id].append(event)
            
            # Clean old windows
            current_time = event.timestamp.timestamp()
            while self.aggregation_windows[device_id]:
                oldest = self.aggregation_windows[device_id][0]
                if (current_time - oldest.timestamp.timestamp()) > (self.window_size_ms / 1000):
                    self.aggregation_windows[device_id].popleft()
                else:
                    break
            
            # Return aggregated metrics if we have data
            if self.aggregation_windows[device_id]:
                events = list(self.aggregation_windows[device_id])
                values = [e.data.get("value", 0) for e in events if "value" in e.data]
                
                if values:
                    return AggregatedMetrics(
                        device_id=device_id,
                        window_start=events[0].timestamp,
                        window_end=events[-1].timestamp,
                        metric_count=len(events),
                        avg_value=sum(values) / len(values),
                        min_value=min(values),
                        max_value=max(values),
                        anomaly_count=sum(1 for e in events if e.event_type == EventType.ANOMALY_DETECTED),
                    )
        
        return None


class BackpressureHandler:
    """Handle backpressure for high-volume event streams."""
    
    def __init__(self, max_queue_size: int = 10000, max_processing_rate: int = 1000):
        """
        Initialize backpressure handler.
        
        Args:
            max_queue_size: Maximum events in queue before applying backpressure
            max_processing_rate: Maximum events per second to process
        """
        self.max_queue_size = max_queue_size
        self.max_processing_rate = max_processing_rate
        self.queue: deque = deque()
        self.lock = Lock()
        self.event_count = 0
        self.last_reset_time = datetime.now()
    
    def can_accept(self) -> bool:
        """Check if queue can accept more events."""
        with self.lock:
            return len(self.queue) < self.max_queue_size
    
    def enqueue(self, event: Event) -> bool:
        """
        Enqueue event with backpressure handling.
        
        Args:
            event: Event to enqueue
            
        Returns:
            True if event was enqueued, False if backpressure applied
        """
        with self.lock:
            if len(self.queue) >= self.max_queue_size:
                logger.warning(f"Backpressure applied: queue size {len(self.queue)}")
                return False
            
            self.queue.append(event)
            return True
    
    def dequeue(self) -> Optional[Event]:
        """
        Dequeue event with rate limiting.
        
        Returns:
            Event if available and rate limit not exceeded, None otherwise
        """
        with self.lock:
            now = datetime.now()
            elapsed = (now - self.last_reset_time).total_seconds()
            
            # Reset counter every second
            if elapsed >= 1.0:
                self.event_count = 0
                self.last_reset_time = now
            
            # Check rate limit
            if self.event_count >= self.max_processing_rate:
                return None
            
            if self.queue:
                self.event_count += 1
                return self.queue.popleft()
        
        return None
    
    def queue_size(self) -> int:
        """Get current queue size."""
        with self.lock:
            return len(self.queue)


class KafkaConsumerGroup:
    """Kafka consumer group for device metrics and anomaly streams."""
    
    def __init__(
        self,
        group_id: str,
        topics: List[str],
        max_queue_size: int = 10000,
        max_processing_rate: int = 1000,
    ):
        """
        Initialize Kafka consumer group.
        
        Args:
            group_id: Consumer group identifier
            topics: List of topics to subscribe to
            max_queue_size: Maximum events in queue
            max_processing_rate: Maximum events per second
        """
        self.group_id = group_id
        self.topics = topics
        self.backpressure_handler = BackpressureHandler(max_queue_size, max_processing_rate)
        self.event_processor = EventProcessor()
        self.callbacks: List[Callable[[Event], None]] = []
        self.is_running = False
        self.consumer_thread: Optional[Thread] = None
        self.stop_event = ThreadingEvent()
    
    def add_filter(self, event_filter: EventFilter) -> None:
        """Add filter to event processor."""
        self.event_processor.add_filter(event_filter)
    
    def subscribe(self, callback: Callable[[Event], None]) -> None:
        """
        Subscribe to processed events.
        
        Args:
            callback: Function to call when event is processed
        """
        self.callbacks.append(callback)
    
    def start(self) -> None:
        """Start consuming events."""
        if self.is_running:
            logger.warning("Consumer group already running")
            return
        
        self.is_running = True
        self.stop_event.clear()
        self.consumer_thread = Thread(target=self._consume_loop, daemon=True)
        self.consumer_thread.start()
        logger.info(f"Started consumer group {self.group_id} for topics {self.topics}")
    
    def stop(self) -> None:
        """Stop consuming events."""
        if not self.is_running:
            return
        
        self.is_running = False
        self.stop_event.set()
        
        if self.consumer_thread:
            self.consumer_thread.join(timeout=5)
        
        logger.info(f"Stopped consumer group {self.group_id}")
    
    def _consume_loop(self) -> None:
        """Main consumption loop (runs in separate thread)."""
        while not self.stop_event.is_set():
            # Dequeue event with rate limiting
            event = self.backpressure_handler.dequeue()
            
            if event is None:
                # No event available or rate limit reached
                time.sleep(0.01)  # Sleep briefly to avoid busy waiting
                continue
            
            # Process event through filters
            processed_event = self.event_processor.process(event)
            
            if processed_event:
                # Call all subscribers
                for callback in self.callbacks:
                    try:
                        callback(processed_event)
                    except Exception as e:
                        logger.error(f"Error in callback: {e}")
    
    def push_event(self, event: Event) -> bool:
        """
        Push event to consumer group.
        
        Args:
            event: Event to push
            
        Returns:
            True if event was accepted, False if backpressure applied
        """
        return self.backpressure_handler.enqueue(event)
    
    def get_queue_size(self) -> int:
        """Get current queue size."""
        return self.backpressure_handler.queue_size()
    
    def get_status(self) -> Dict[str, Any]:
        """Get consumer group status."""
        return {
            "group_id": self.group_id,
            "topics": self.topics,
            "is_running": self.is_running,
            "queue_size": self.get_queue_size(),
            "max_queue_size": self.backpressure_handler.max_queue_size,
            "max_processing_rate": self.backpressure_handler.max_processing_rate,
        }


class EventStreamingManager:
    """Manage multiple Kafka consumer groups and event streams."""
    
    def __init__(self):
        """Initialize event streaming manager."""
        self.consumer_groups: Dict[str, KafkaConsumerGroup] = {}
        self.lock = Lock()
    
    def create_consumer_group(
        self,
        group_id: str,
        topics: List[str],
        max_queue_size: int = 10000,
        max_processing_rate: int = 1000,
    ) -> KafkaConsumerGroup:
        """
        Create a new consumer group.
        
        Args:
            group_id: Consumer group identifier
            topics: List of topics to subscribe to
            max_queue_size: Maximum events in queue
            max_processing_rate: Maximum events per second
            
        Returns:
            Created consumer group
        """
        with self.lock:
            if group_id in self.consumer_groups:
                raise ValueError(f"Consumer group {group_id} already exists")
            
            consumer_group = KafkaConsumerGroup(
                group_id=group_id,
                topics=topics,
                max_queue_size=max_queue_size,
                max_processing_rate=max_processing_rate,
            )
            self.consumer_groups[group_id] = consumer_group
            return consumer_group
    
    def get_consumer_group(self, group_id: str) -> Optional[KafkaConsumerGroup]:
        """Get consumer group by ID."""
        return self.consumer_groups.get(group_id)
    
    def start_all(self) -> None:
        """Start all consumer groups."""
        with self.lock:
            for consumer_group in self.consumer_groups.values():
                consumer_group.start()
    
    def stop_all(self) -> None:
        """Stop all consumer groups."""
        with self.lock:
            for consumer_group in self.consumer_groups.values():
                consumer_group.stop()
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all consumer groups."""
        with self.lock:
            return {
                group_id: group.get_status()
                for group_id, group in self.consumer_groups.items()
            }


# Global event streaming manager instance
_event_streaming_manager: Optional[EventStreamingManager] = None


def get_event_streaming_manager() -> EventStreamingManager:
    """Get or create global event streaming manager."""
    global _event_streaming_manager
    if _event_streaming_manager is None:
        _event_streaming_manager = EventStreamingManager()
    return _event_streaming_manager
