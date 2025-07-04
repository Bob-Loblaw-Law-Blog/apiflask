"""
Production-Ready API Example for APIFlask
=========================================

This example demonstrates production-ready patterns including:
- Environment-based configuration
- Comprehensive logging
- Health checks and monitoring
- Rate limiting
- Caching
- Security headers
- Request/response middleware
- Performance monitoring
"""

import os
import time
import logging
import json
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Any, Optional

from apiflask import APIFlask, Schema, abort
from apiflask.fields import Integer, String, DateTime, Float, Nested
from flask import request, g, current_app
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from werkzeug.middleware.profiler import ProfilerMiddleware
from werkzeug.middleware.proxy_fix import ProxyFix


# Environment Configuration
class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Redis configuration
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379'
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = REDIS_URL
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_DEFAULT = "100/hour"
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s'
    
    # Security
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Monitoring
    ENABLE_PROFILER = os.environ.get('ENABLE_PROFILER', 'false').lower() == 'true'


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///dev.db'
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///prod.db'
    LOG_LEVEL = 'WARNING'
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'https://yourdomain.com').split(',')


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    CACHE_TYPE = 'simple'
    RATELIMIT_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


# Application Factory
def create_app(config_name='default'):
    """Application factory pattern."""
    app = APIFlask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    setup_extensions(app)
    setup_logging(app)
    setup_middleware(app)
    setup_routes(app)
    setup_error_handlers(app)
    
    return app


def setup_extensions(app):
    """Initialize Flask extensions."""
    # CORS
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Caching
    cache = Cache(app)
    app.cache = cache
    
    # Rate Limiting
    limiter = Limiter(
        app,
        key_func=get_remote_address,
        default_limits=[app.config['RATELIMIT_DEFAULT']]
    )
    app.limiter = limiter


def setup_logging(app):
    """Configure comprehensive logging."""
    import logging.handlers
    
    # Create logs directory
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure root logger
    logging.basicConfig(level=getattr(logging, app.config['LOG_LEVEL']))
    
    # File handler for application logs
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(app.config['LOG_FORMAT']))
    file_handler.setLevel(logging.INFO)
    
    # File handler for error logs
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'error.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_handler.setFormatter(logging.Formatter(app.config['LOG_FORMAT']))
    error_handler.setLevel(logging.ERROR)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(app.config['LOG_FORMAT']))
    
    # Add handlers to app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))


def setup_middleware(app):
    """Setup middleware for production."""
    # Proxy fix for handling reverse proxy headers
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Optional profiler for performance monitoring
    if app.config.get('ENABLE_PROFILER'):
        app.wsgi_app = ProfilerMiddleware(
            app.wsgi_app, 
            sort_by=('cumulative', 'time'),
            restrictions=(30,)
        )


def setup_routes(app):
    """Setup application routes."""
    
    # Request ID middleware
    @app.before_request
    def before_request():
        """Add request ID and start time for tracking."""
        import uuid
        g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        g.start_time = time.time()
        
        # Log incoming request
        app.logger.info(
            f"Incoming {request.method} request to {request.url}",
            extra={'request_id': g.request_id}
        )
    
    # Response middleware
    @app.after_request
    def after_request(response):
        """Add security headers and log response."""
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-Request-ID'] = g.request_id
        
        # Performance headers
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            response.headers['X-Response-Time'] = f"{duration:.3f}s"
        
        # Log response
        app.logger.info(
            f"Response {response.status_code} in {duration:.3f}s",
            extra={'request_id': g.request_id}
        )
        
        return response
    
    # Health check endpoints
    @app.get('/health')
    def health_check():
        """Basic health check."""
        return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}
    
    @app.get('/health/detailed')
    def detailed_health_check():
        """Detailed health check with dependency status."""
        status = {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}
        
        # Check cache
        try:
            app.cache.set('health_check', 'ok', timeout=1)
            cache_status = app.cache.get('health_check') == 'ok'
        except Exception as e:
            cache_status = False
            app.logger.error(f"Cache health check failed: {str(e)}")
        
        status['dependencies'] = {
            'cache': 'healthy' if cache_status else 'unhealthy'
        }
        
        # Overall status
        if not cache_status:
            status['status'] = 'degraded'
        
        return status
    
    # Metrics endpoint
    @app.get('/metrics')
    @app.limiter.limit("10/minute")
    def metrics():
        """Application metrics for monitoring."""
        import psutil
        import gc
        
        try:
            process = psutil.Process()
            
            metrics_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'system': {
                    'cpu_percent': psutil.cpu_percent(),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_usage': psutil.disk_usage('/').percent
                },
                'process': {
                    'memory_rss': process.memory_info().rss,
                    'memory_vms': process.memory_info().vms,
                    'cpu_percent': process.cpu_percent(),
                    'num_threads': process.num_threads(),
                    'open_files': len(process.open_files())
                },
                'python': {
                    'gc_counts': gc.get_count(),
                    'gc_stats': gc.get_stats() if hasattr(gc, 'get_stats') else None
                }
            }
            
            return metrics_data
        except Exception as e:
            app.logger.error(f"Error collecting metrics: {str(e)}")
            return {'error': 'Failed to collect metrics'}, 500
    
    # Example API endpoints
    
    class TaskSchema(Schema):
        title = String(required=True)
        description = String()
        priority = Integer(missing=1)
    
    class TaskResponseSchema(Schema):
        id = Integer()
        title = String()
        description = String()
        priority = Integer()
        created_at = DateTime()
        cached = Integer(missing=0)  # Indicates if response was cached
    
    # In-memory storage for demo
    tasks = []
    task_counter = 0
    
    @app.get('/api/tasks')
    @app.output(TaskResponseSchema(many=True))
    @app.limiter.limit("60/minute")
    @app.cache.cached(timeout=300, key_prefix='all_tasks')  # 5-minute cache
    def get_all_tasks():
        """Get all tasks with caching."""
        app.logger.info("Fetching all tasks")
        
        # Add cached indicator
        cached_tasks = []
        for task in tasks:
            task_copy = task.copy()
            task_copy['cached'] = 1
            cached_tasks.append(task_copy)
        
        return cached_tasks
    
    @app.get('/api/tasks/<int:task_id>')
    @app.output(TaskResponseSchema)
    @app.limiter.limit("100/minute")
    def get_task(task_id: int):
        """Get specific task with caching."""
        cache_key = f'task_{task_id}'
        
        # Try cache first
        cached_task = app.cache.get(cache_key)
        if cached_task:
            app.logger.info(f"Task {task_id} served from cache")
            cached_task['cached'] = 1
            return cached_task
        
        # Find task
        task = next((t for t in tasks if t['id'] == task_id), None)
        if not task:
            abort(404, message='Task not found')
        
        # Cache the result
        app.cache.set(cache_key, task, timeout=300)
        app.logger.info(f"Task {task_id} cached")
        
        task_copy = task.copy()
        task_copy['cached'] = 0
        return task_copy
    
    @app.post('/api/tasks')
    @app.input(TaskSchema)
    @app.output(TaskResponseSchema, status_code=201)
    @app.limiter.limit("30/minute")  # Stricter limit for writes
    def create_task(json_data):
        """Create new task and invalidate cache."""
        nonlocal task_counter
        task_counter += 1
        
        new_task = {
            'id': task_counter,
            'title': json_data['title'],
            'description': json_data.get('description', ''),
            'priority': json_data['priority'],
            'created_at': datetime.utcnow()
        }
        
        tasks.append(new_task)
        
        # Invalidate cache
        app.cache.delete('all_tasks')
        app.logger.info(f"Created task {task_counter}, cache invalidated")
        
        new_task_copy = new_task.copy()
        new_task_copy['cached'] = 0
        return new_task_copy
    
    @app.delete('/api/tasks/<int:task_id>')
    @app.output({}, status_code=204)
    @app.limiter.limit("20/minute")
    def delete_task(task_id: int):
        """Delete task and invalidate cache."""
        task = next((t for t in tasks if t['id'] == task_id), None)
        if not task:
            abort(404, message='Task not found')
        
        tasks.remove(task)
        
        # Invalidate cache
        app.cache.delete('all_tasks')
        app.cache.delete(f'task_{task_id}')
        app.logger.info(f"Deleted task {task_id}, cache invalidated")
        
        return ''
    
    # Demonstration endpoints for various scenarios
    
    @app.get('/api/slow')
    @app.limiter.limit("5/minute")  # Very strict limit for expensive operations
    def slow_endpoint():
        """Simulate slow endpoint for testing timeouts."""
        import time
        delay = request.args.get('delay', 1, type=float)
        time.sleep(min(delay, 10))  # Cap at 10 seconds
        return {'message': f'Completed after {delay} seconds'}
    
    @app.get('/api/error-demo')
    def error_demo():
        """Demonstrate error handling and logging."""
        error_type = request.args.get('type', 'generic')
        
        if error_type == 'validation':
            abort(400, message='Invalid input provided')
        elif error_type == 'not-found':
            abort(404, message='Resource not found')
        elif error_type == 'server':
            raise Exception('Simulated server error')
        else:
            return {'message': 'No error triggered'}
    
    @app.get('/api/secured')
    def secured_endpoint():
        """Example of endpoint that could require authentication."""
        # This would normally check authentication
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            abort(401, message='API key required')
        
        return {'message': 'Access granted', 'api_key': api_key[:8] + '...'}


def setup_error_handlers(app):
    """Setup centralized error handling."""
    
    @app.errorhandler(429)
    def ratelimit_handler(error):
        """Handle rate limit exceeded."""
        app.logger.warning(
            f"Rate limit exceeded for {request.remote_addr}",
            extra={'request_id': getattr(g, 'request_id', 'unknown')}
        )
        return {
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please try again later.',
            'retry_after': error.retry_after
        }, 429
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle unexpected exceptions."""
        import traceback
        
        app.logger.error(
            f"Unexpected error: {str(error)}",
            extra={
                'request_id': getattr(g, 'request_id', 'unknown'),
                'traceback': traceback.format_exc()
            }
        )
        
        if app.debug:
            return {
                'error': 'Internal server error',
                'message': str(error),
                'traceback': traceback.format_exc()
            }, 500
        else:
            return {
                'error': 'Internal server error',
                'message': 'An unexpected error occurred'
            }, 500


# Performance monitoring decorator
def monitor_performance(threshold_seconds=1.0):
    """Decorator to monitor endpoint performance."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            result = f(*args, **kwargs)
            duration = time.time() - start_time
            
            if duration > threshold_seconds:
                current_app.logger.warning(
                    f"Slow endpoint {request.endpoint}: {duration:.3f}s",
                    extra={'request_id': getattr(g, 'request_id', 'unknown')}
                )
            
            return result
        return decorated_function
    return decorator


# Create application instance
app = create_app(os.environ.get('FLASK_ENV', 'development'))


if __name__ == '__main__':
    # Get configuration
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.logger.info(f"Starting application on {host}:{port}")
    app.run(host=host, port=port, debug=debug)


"""
Production Deployment Guide:
===========================

1. Environment Variables:
   export FLASK_ENV=production
   export SECRET_KEY=your-secret-key
   export DATABASE_URL=postgresql://user:pass@localhost/db
   export REDIS_URL=redis://localhost:6379
   export CORS_ORIGINS=https://yourdomain.com

2. Dependencies for production:
   pip install redis flask-caching flask-limiter flask-cors psutil

3. Running with Gunicorn:
   gunicorn -w 4 -b 0.0.0.0:5000 "production_ready_example:create_app('production')"

4. Docker deployment:
   FROM python:3.9-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   EXPOSE 5000
   CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "production_ready_example:create_app('production')"]

5. Nginx reverse proxy configuration:
   server {
       listen 80;
       server_name yourdomain.com;
       
       location / {
           proxy_pass http://localhost:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       }
   }

6. Monitoring endpoints:
   - GET /health - Basic health check
   - GET /health/detailed - Health check with dependencies
   - GET /metrics - Application metrics

7. Security features:
   - CORS configuration
   - Security headers
   - Rate limiting
   - Request ID tracking
   - Input validation

8. Performance features:
   - Redis caching
   - Response time headers
   - Performance monitoring
   - Request/response logging
   - Metrics collection

This example provides a solid foundation for deploying APIFlask
applications in production environments.
"""
