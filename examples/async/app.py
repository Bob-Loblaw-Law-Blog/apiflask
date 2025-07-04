"""
Async API Example for APIFlask
=================================

This example demonstrates how to use async/await with APIFlask,
including async database operations, background tasks, and
concurrent request handling.

Requirements:
- pip install "apiflask[async]"
- pip install aiofiles
- pip install aiohttp
"""

import asyncio
import aiofiles
import aiohttp
import time
from datetime import datetime
from pathlib import Path

from apiflask import APIFlask, Schema, abort
from apiflask.fields import Integer, String, DateTime, Float
from apiflask.validators import Length, Range


app = APIFlask(__name__)

# Simulated async database
tasks_db = []
task_id_counter = 0

# Background task storage
background_tasks = {}


class TaskIn(Schema):
    title = String(required=True, validate=Length(1, 100))
    description = String(allow_none=True, validate=Length(0, 500))
    priority = Integer(validate=Range(1, 5), load_default=3)


class TaskOut(Schema):
    id = Integer()
    title = String()
    description = String()
    priority = Integer()
    created_at = DateTime()
    completed = Boolean()


class BackgroundTaskOut(Schema):
    task_id = String()
    status = String()
    progress = Float()
    result = String(allow_none=True)


@app.get('/')
async def hello():
    """Async hello endpoint that simulates some async work."""
    await asyncio.sleep(0.1)  # Simulate async work
    return {'message': 'Hello from async APIFlask!', 'timestamp': datetime.utcnow().isoformat()}


@app.get('/tasks')
@app.output(TaskOut(many=True))
async def get_tasks():
    """Get all tasks asynchronously."""
    # Simulate async database query
    await asyncio.sleep(0.05)
    return tasks_db


@app.get('/tasks/<int:task_id>')
@app.output(TaskOut)
async def get_task(task_id):
    """Get a specific task asynchronously."""
    await asyncio.sleep(0.05)  # Simulate async DB lookup
    
    task = next((task for task in tasks_db if task['id'] == task_id), None)
    if not task:
        abort(404, message='Task not found')
    
    return task


@app.post('/tasks')
@app.input(TaskIn)
@app.output(TaskOut, status_code=201)
async def create_task(json_data):
    """Create a new task asynchronously."""
    global task_id_counter
    
    # Simulate async validation or external service call
    await asyncio.sleep(0.1)
    
    task_id_counter += 1
    new_task = {
        'id': task_id_counter,
        'title': json_data['title'],
        'description': json_data.get('description', ''),
        'priority': json_data['priority'],
        'created_at': datetime.utcnow(),
        'completed': False
    }
    
    tasks_db.append(new_task)
    return new_task


@app.patch('/tasks/<int:task_id>')
@app.input(TaskIn(partial=True))
@app.output(TaskOut)
async def update_task(task_id, json_data):
    """Update a task asynchronously."""
    await asyncio.sleep(0.05)
    
    task = next((task for task in tasks_db if task['id'] == task_id), None)
    if not task:
        abort(404, message='Task not found')
    
    # Simulate async validation
    if 'title' in json_data:
        await asyncio.sleep(0.02)  # Validate title uniqueness
    
    for key, value in json_data.items():
        task[key] = value
    
    return task


@app.post('/tasks/<int:task_id>/process')
@app.output(BackgroundTaskOut, status_code=202)
async def process_task(task_id):
    """Start background processing for a task."""
    # Find the task
    task = next((task for task in tasks_db if task['id'] == task_id), None)
    if not task:
        abort(404, message='Task not found')
    
    # Create background task
    bg_task_id = f"bg_{task_id}_{int(time.time())}"
    
    # Start background task
    asyncio.create_task(background_task_runner(bg_task_id, task))
    
    background_tasks[bg_task_id] = {
        'task_id': bg_task_id,
        'status': 'running',
        'progress': 0.0,
        'result': None
    }
    
    return background_tasks[bg_task_id]


@app.get('/background-tasks/<task_id>')
@app.output(BackgroundTaskOut)
async def get_background_task_status(task_id):
    """Check the status of a background task."""
    if task_id not in background_tasks:
        abort(404, message='Background task not found')
    
    return background_tasks[task_id]


@app.get('/external-data')
async def fetch_external_data():
    """Fetch data from external API asynchronously."""
    try:
        async with aiohttp.ClientSession() as session:
            # Example: fetch from a public API
            async with session.get('https://httpbin.org/json') as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'external_data': data,
                        'fetched_at': datetime.utcnow().isoformat()
                    }
                else:
                    abort(502, message='Failed to fetch external data')
    except Exception as e:
        abort(502, message=f'External API error: {str(e)}')


@app.post('/files/upload')
async def upload_file_async():
    """Handle file upload asynchronously."""
    # Note: This is a simplified example. In practice, you'd use proper file handling
    upload_dir = Path('./uploads')
    upload_dir.mkdir(exist_ok=True)
    
    # Simulate async file processing
    filename = f"async_file_{int(time.time())}.txt"
    filepath = upload_dir / filename
    
    # Simulate writing large file asynchronously
    async with aiofiles.open(filepath, 'w') as f:
        await f.write(f"Async file created at {datetime.utcnow().isoformat()}")
        await asyncio.sleep(0.1)  # Simulate processing time
    
    return {
        'message': f'File {filename} uploaded successfully',
        'processed_async': True
    }


@app.get('/concurrent-demo')
async def concurrent_operations_demo():
    """Demonstrate concurrent async operations."""
    start_time = time.time()
    
    # Run multiple async operations concurrently
    async def operation_1():
        await asyncio.sleep(0.1)
        return {'op1': 'completed', 'duration': 0.1}
    
    async def operation_2():
        await asyncio.sleep(0.15)
        return {'op2': 'completed', 'duration': 0.15}
    
    async def operation_3():
        await asyncio.sleep(0.08)
        return {'op3': 'completed', 'duration': 0.08}
    
    # Run operations concurrently
    results = await asyncio.gather(
        operation_1(),
        operation_2(),
        operation_3()
    )
    
    total_time = time.time() - start_time
    
    return {
        'results': results,
        'total_execution_time': round(total_time, 3),
        'note': 'Operations ran concurrently, not sequentially'
    }


async def background_task_runner(task_id: str, task_data: dict):
    """Simulate a long-running background task."""
    try:
        # Update status to running
        background_tasks[task_id]['status'] = 'running'
        
        # Simulate work with progress updates
        for progress in [0.2, 0.4, 0.6, 0.8, 1.0]:
            await asyncio.sleep(0.5)  # Simulate work
            background_tasks[task_id]['progress'] = progress
        
        # Complete the task
        background_tasks[task_id]['status'] = 'completed'
        background_tasks[task_id]['result'] = f"Task '{task_data['title']}' processed successfully"
        
        # Mark the original task as completed
        task_data['completed'] = True
        
    except Exception as e:
        background_tasks[task_id]['status'] = 'failed'
        background_tasks[task_id]['result'] = f"Error: {str(e)}"


# Error handler for async operations
@app.errorhandler(asyncio.TimeoutError)
async def handle_timeout_error(error):
    return {
        'error': 'Request timeout',
        'message': 'The async operation took too long to complete'
    }, 408


@app.errorhandler(aiohttp.ClientError)
async def handle_http_error(error):
    return {
        'error': 'External service error',
        'message': f'Failed to communicate with external service: {str(error)}'
    }, 502


if __name__ == '__main__':
    # For development - use proper ASGI server (like uvicorn) in production
    app.run(debug=True, host='0.0.0.0', port=5000)


"""
Usage Examples:

1. Test concurrent operations:
   GET /concurrent-demo

2. Create and process tasks:
   POST /tasks {"title": "Test Task", "description": "Test", "priority": 2}
   POST /tasks/1/process
   GET /background-tasks/bg_1_1234567890

3. Fetch external data:
   GET /external-data

4. Upload file asynchronously:
   POST /files/upload

Note: To run this with proper async support, use an ASGI server:
pip install uvicorn
uvicorn async_api_example:app --reload
"""
