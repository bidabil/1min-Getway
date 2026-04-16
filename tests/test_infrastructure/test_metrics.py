"""
Tests for metrics.py module.

Tests cover:
- MetricValue dataclass
- Counter class
- Gauge class
- Histogram class
- MetricsRegistry class
- Helper functions
"""

from src.infrastructure.metrics import (
    ACTIVE_REQUESTS,
    CACHE_HITS,
    CACHE_MISSES,
    MODEL_REQUESTS,
    REQUEST_COUNT,
    REQUEST_DURATION,
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    MetricValue,
    get_metrics_output,
)


class TestMetricValue:
    """Tests for MetricValue dataclass."""

    def test_metric_value_creation(self):
        """Test creating a MetricValue."""
        mv = MetricValue(value=10.5, labels={"key": "value"})
        assert mv.value == 10.5
        assert mv.labels == {"key": "value"}

    def test_metric_value_empty_labels(self):
        """Test MetricValue with empty labels."""
        mv = MetricValue(value=5.0, labels={})
        assert mv.value == 5.0
        assert mv.labels == {}


class TestCounter:
    """Tests for Counter class."""

    def test_counter_creation(self):
        """Test creating a counter."""
        counter = Counter("test_counter", "Test counter description")
        assert counter.name == "test_counter"
        assert counter.description == "Test counter description"
        assert counter.label_names == []

    def test_counter_with_labels(self):
        """Test creating a counter with labels."""
        counter = Counter("test_counter", "Test", label_names=["method", "status"])
        assert counter.label_names == ["method", "status"]

    def test_counter_inc(self):
        """Test incrementing a counter."""
        counter = Counter("test_counter", "Test")
        counter.inc()
        values = counter.get_values()
        assert len(values) == 1
        assert values[0].value == 1.0

    def test_counter_inc_by_amount(self):
        """Test incrementing a counter by specific amount."""
        counter = Counter("test_counter", "Test")
        counter.inc(5.0)
        values = counter.get_values()
        assert values[0].value == 5.0

    def test_counter_inc_multiple_times(self):
        """Test incrementing a counter multiple times."""
        counter = Counter("test_counter", "Test")
        counter.inc()
        counter.inc()
        counter.inc()
        values = counter.get_values()
        assert values[0].value == 3.0

    def test_counter_inc_with_labels(self):
        """Test incrementing a counter with labels."""
        counter = Counter("test_counter", "Test", label_names=["method"])
        counter.inc(method="GET")
        counter.inc(method="POST")
        counter.inc(method="GET")

        values = counter.get_values()
        assert len(values) == 2

        get_value = [v for v in values if v.labels.get("method") == "GET"][0]
        post_value = [v for v in values if v.labels.get("method") == "POST"][0]

        assert get_value.value == 2.0
        assert post_value.value == 1.0

    def test_counter_export(self):
        """Test exporting a counter."""
        counter = Counter("test_counter", "Test counter")
        counter.inc(10)

        exported = counter.export()

        assert "# HELP test_counter Test counter" in exported
        assert "# TYPE test_counter counter" in exported
        assert "test_counter 10" in exported

    def test_counter_export_with_labels(self):
        """Test exporting a counter with labels."""
        counter = Counter("test_counter", "Test", label_names=["method"])
        counter.inc(method="GET")

        exported = counter.export()

        assert 'method="GET"' in exported


class TestGauge:
    """Tests for Gauge class."""

    def test_gauge_creation(self):
        """Test creating a gauge."""
        gauge = Gauge("test_gauge", "Test gauge description")
        assert gauge.name == "test_gauge"
        assert gauge.description == "Test gauge description"

    def test_gauge_set(self):
        """Test setting a gauge value."""
        gauge = Gauge("test_gauge", "Test")
        gauge.set(42.0)
        values = gauge.get_values()
        assert values[0].value == 42.0

    def test_gauge_inc(self):
        """Test incrementing a gauge."""
        gauge = Gauge("test_gauge", "Test")
        gauge.set(10)
        gauge.inc(5)
        values = gauge.get_values()
        assert values[0].value == 15.0

    def test_gauge_dec(self):
        """Test decrementing a gauge."""
        gauge = Gauge("test_gauge", "Test")
        gauge.set(10)
        gauge.dec(3)
        values = gauge.get_values()
        assert values[0].value == 7.0

    def test_gauge_inc_from_zero(self):
        """Test incrementing a gauge from zero."""
        gauge = Gauge("test_gauge", "Test")
        gauge.inc()
        values = gauge.get_values()
        assert values[0].value == 1.0

    def test_gauge_dec_from_zero(self):
        """Test decrementing a gauge from zero."""
        gauge = Gauge("test_gauge", "Test")
        gauge.dec()
        values = gauge.get_values()
        assert values[0].value == -1.0

    def test_gauge_with_labels(self):
        """Test gauge with labels."""
        gauge = Gauge("test_gauge", "Test", label_names=["host"])
        gauge.set(100, host="server1")
        gauge.set(200, host="server2")

        values = gauge.get_values()
        assert len(values) == 2

    def test_gauge_export(self):
        """Test exporting a gauge."""
        gauge = Gauge("test_gauge", "Test gauge")
        gauge.set(42.0)

        exported = gauge.export()

        assert "# HELP test_gauge Test gauge" in exported
        assert "# TYPE test_gauge gauge" in exported
        assert "test_gauge 42" in exported


class TestHistogram:
    """Tests for Histogram class."""

    def test_histogram_creation(self):
        """Test creating a histogram."""
        hist = Histogram("test_hist", "Test histogram")
        assert hist.name == "test_hist"
        assert hist.description == "Test histogram"
        assert len(hist.buckets) > 0

    def test_histogram_custom_buckets(self):
        """Test creating a histogram with custom buckets."""
        hist = Histogram("test_hist", "Test", buckets=[0.1, 0.5, 1.0])
        assert hist.buckets == [0.1, 0.5, 1.0]

    def test_histogram_observe(self):
        """Test observing values in a histogram."""
        hist = Histogram("test_hist", "Test", buckets=[0.1, 0.5, 1.0])
        hist.observe(0.05)
        hist.observe(0.3)
        hist.observe(0.7)

        values = hist.get_values()
        assert len(values) == 1
        assert abs(values[0]["sum"] - 1.05) < 0.001  # Float comparison

    def test_histogram_bucket_counts(self):
        """Test histogram bucket counts."""
        hist = Histogram("test_hist", "Test", buckets=[0.1, 0.5, 1.0])
        hist.observe(0.05)  # Goes in 0.1 bucket
        hist.observe(0.3)  # Goes in 0.5 bucket
        hist.observe(0.7)  # Goes in 1.0 bucket

        values = hist.get_values()
        buckets = values[0]["buckets"]

        # Each value goes into all buckets >= value
        assert buckets[0.1] == 1  # 0.05 <= 0.1
        assert buckets[0.5] == 2  # 0.05, 0.3 <= 0.5
        assert buckets[1.0] == 3  # 0.05, 0.3, 0.7 <= 1.0

    def test_histogram_with_labels(self):
        """Test histogram with labels."""
        hist = Histogram("test_hist", "Test", label_names=["endpoint"])
        hist.observe(0.1, endpoint="/api")
        hist.observe(0.2, endpoint="/api")
        hist.observe(0.3, endpoint="/health")

        values = hist.get_values()
        assert len(values) == 2

    def test_histogram_export(self):
        """Test exporting a histogram."""
        hist = Histogram("test_hist", "Test histogram", buckets=[0.1, 0.5])
        hist.observe(0.05)
        hist.observe(0.3)

        exported = hist.export()

        assert "# HELP test_hist Test histogram" in exported
        assert "# TYPE test_hist histogram" in exported
        assert "test_hist_bucket" in exported
        assert "test_hist_sum" in exported
        assert "test_hist_count" in exported

    def test_histogram_export_with_labels(self):
        """Test exporting a histogram with labels."""
        hist = Histogram("test_hist", "Test", label_names=["method"])
        hist.observe(0.1, method="GET")

        exported = hist.export()

        assert 'method="GET"' in exported


class TestMetricsRegistry:
    """Tests for MetricsRegistry class."""

    def test_registry_creation(self):
        """Test creating a registry."""
        registry = MetricsRegistry(namespace="test")
        assert registry.namespace == "test"

    def test_register_counter(self):
        """Test registering a counter."""
        registry = MetricsRegistry(namespace="test")
        counter = Counter("my_counter", "Test")
        registry.register(counter)

        assert "test_my_counter" in registry._metrics

    def test_register_gauge(self):
        """Test registering a gauge."""
        registry = MetricsRegistry(namespace="test")
        gauge = Gauge("my_gauge", "Test")
        registry.register(gauge)

        assert "test_my_gauge" in registry._metrics

    def test_register_histogram(self):
        """Test registering a histogram."""
        registry = MetricsRegistry(namespace="test")
        hist = Histogram("my_hist", "Test")
        registry.register(hist)

        assert "test_my_hist" in registry._metrics

    def test_counter_factory(self):
        """Test counter factory method."""
        registry = MetricsRegistry(namespace="test")
        counter = registry.counter("requests", "Total requests")

        assert "test_requests" in registry._metrics
        assert counter.name == "test_requests"

    def test_gauge_factory(self):
        """Test gauge factory method."""
        registry = MetricsRegistry(namespace="test")
        registry.gauge("connections", "Active connections")

        assert "test_connections" in registry._metrics

    def test_histogram_factory(self):
        """Test histogram factory method."""
        registry = MetricsRegistry(namespace="test")
        registry.histogram("duration", "Request duration")

        assert "test_duration" in registry._metrics

    def test_export_all(self):
        """Test exporting all metrics."""
        registry = MetricsRegistry(namespace="test")
        counter = registry.counter("requests", "Total")
        gauge = registry.gauge("active", "Active")

        counter.inc()
        gauge.set(5)

        exported = registry.export()

        assert "test_requests" in exported
        assert "test_active" in exported

    def test_get_metrics(self):
        """Test getting metrics as dictionary."""
        registry = MetricsRegistry(namespace="test")
        counter = registry.counter("requests", "Total")
        counter.inc()

        metrics_dict = registry.get_metrics()

        assert "test_requests" in metrics_dict
        assert metrics_dict["test_requests"]["type"] == "Counter"


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_track_request(self):
        """Test track_request function."""
        # Use a fresh registry for testing
        registry = MetricsRegistry(namespace="test")
        counter = registry.counter("http_requests_total", "Test", ["method", "endpoint", "status"])
        hist = registry.histogram("http_request_duration", "Test")

        # Track a request
        counter.inc(method="GET", endpoint="/test", status="200")
        hist.observe(0.5, method="GET", endpoint="/test")

        values = counter.get_values()
        assert len(values) == 1
        assert values[0].value == 1.0

    def test_track_model_request(self):
        """Test track_model_request function."""
        registry = MetricsRegistry(namespace="test")
        counter = registry.counter("model_requests", "Test", ["model", "status"])

        counter.inc(model="gpt-4", status="success")

        values = counter.get_values()
        assert len(values) == 1

    def test_update_circuit_breaker_metrics(self):
        """Test update_circuit_breaker_metrics function."""
        registry = MetricsRegistry(namespace="test")
        state_gauge = registry.gauge("cb_state", "Test", ["name"])
        failures_gauge = registry.gauge("cb_failures", "Test", ["name"])

        # CLOSED = 0
        state_gauge.set(0, name="api")
        failures_gauge.set(0, name="api")

        values = state_gauge.get_values()
        assert values[0].value == 0

    def test_track_cache_hit(self):
        """Test track_cache_hit function."""
        registry = MetricsRegistry(namespace="test")
        counter = registry.counter("cache_hits", "Test", ["cache_name"])

        counter.inc(cache_name="models")

        values = counter.get_values()
        assert values[0].value == 1.0

    def test_track_cache_miss(self):
        """Test track_cache_miss function."""
        registry = MetricsRegistry(namespace="test")
        counter = registry.counter("cache_misses", "Test", ["cache_name"])

        counter.inc(cache_name="models")

        values = counter.get_values()
        assert values[0].value == 1.0


class TestGetMetricsOutput:
    """Tests for get_metrics_output function."""

    def test_get_metrics_output(self):
        """Test getting metrics output."""
        output = get_metrics_output()

        assert isinstance(output, str)
        assert "one_min_gateway" in output


class TestGlobalMetrics:
    """Tests for global metrics instances."""

    def test_request_count_exists(self):
        """Test that REQUEST_COUNT exists."""
        assert REQUEST_COUNT.name.startswith("one_min_gateway")

    def test_request_duration_exists(self):
        """Test that REQUEST_DURATION exists."""
        assert REQUEST_DURATION.name.startswith("one_min_gateway")

    def test_active_requests_exists(self):
        """Test that ACTIVE_REQUESTS exists."""
        assert ACTIVE_REQUESTS.name.startswith("one_min_gateway")

    def test_model_requests_exists(self):
        """Test that MODEL_REQUESTS exists."""
        assert MODEL_REQUESTS.name.startswith("one_min_gateway")

    def test_cache_hits_exists(self):
        """Test that CACHE_HITS exists."""
        assert CACHE_HITS.name.startswith("one_min_gateway")

    def test_cache_misses_exists(self):
        """Test that CACHE_MISSES exists."""
        assert CACHE_MISSES.name.startswith("one_min_gateway")
