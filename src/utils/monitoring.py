from prometheus_client import Counter, Histogram, Gauge
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
import time
from typing import Dict, Any
import psutil
import os

# Request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint']
)

# Error metrics
ERROR_COUNT = Counter(
    'http_errors_total',
    'Total number of HTTP errors',
    ['method', 'endpoint', 'error_type']
)

# Resource metrics
CPU_USAGE = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage'
)

MEMORY_USAGE = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes'
)

DISK_USAGE = Gauge(
    'disk_usage_bytes',
    'Disk usage in bytes'
)

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting request metrics"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Start timer
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            status = response.status_code
            error_type = None
        except Exception as e:
            status = 500
            error_type = type(e).__name__
            raise
        
        # Record metrics
        duration = time.time() - start_time
        endpoint = request.url.path
        
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(duration)
        
        if status >= 400:
            ERROR_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                error_type=error_type or f"HTTP_{status}"
            ).inc()
        
        return response

class ResourceMetricsCollector:
    """Collector for system resource metrics"""
    
    @staticmethod
    def collect_metrics():
        """Collect system resource metrics"""
        # CPU usage
        CPU_USAGE.set(psutil.cpu_percent())
        
        # Memory usage
        memory = psutil.Process(os.getpid()).memory_info()
        MEMORY_USAGE.set(memory.rss)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        DISK_USAGE.set(disk.used)
    
    @staticmethod
    def get_metrics() -> Dict[str, Any]:
        """Get current metrics values"""
        return {
            'cpu_usage': CPU_USAGE._value.get(),
            'memory_usage': MEMORY_USAGE._value.get(),
            'disk_usage': DISK_USAGE._value.get()
        }

class DatabaseMetrics:
    """Database performance metrics"""
    
    QUERY_COUNT = Counter(
        'db_queries_total',
        'Total number of database queries',
        ['operation']
    )
    
    QUERY_LATENCY = Histogram(
        'db_query_duration_seconds',
        'Database query latency in seconds',
        ['operation']
    )
    
    @staticmethod
    def record_query(operation: str, duration: float):
        """Record database query metrics"""
        DatabaseMetrics.QUERY_COUNT.labels(operation=operation).inc()
        DatabaseMetrics.QUERY_LATENCY.labels(operation=operation).observe(duration)

class CacheMetrics:
    """Cache performance metrics"""
    
    CACHE_HITS = Counter(
        'cache_hits_total',
        'Total number of cache hits'
    )
    
    CACHE_MISSES = Counter(
        'cache_misses_total',
        'Total number of cache misses'
    )
    
    CACHE_LATENCY = Histogram(
        'cache_operation_duration_seconds',
        'Cache operation latency in seconds',
        ['operation']
    )
    
    @staticmethod
    def record_hit():
        """Record cache hit"""
        CacheMetrics.CACHE_HITS.inc()
    
    @staticmethod
    def record_miss():
        """Record cache miss"""
        CacheMetrics.CACHE_MISSES.inc()
    
    @staticmethod
    def record_operation(operation: str, duration: float):
        """Record cache operation latency"""
        CacheMetrics.CACHE_LATENCY.labels(operation=operation).observe(duration) 