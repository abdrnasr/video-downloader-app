import redis
import os
import httpx
import mimetypes
import asyncio
import uuid
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from urllib.parse import urlparse, parse_qs
from starlette.websockets import WebSocketState

from backendcode.tasks import extract_info,download_video,delete_thumbnail
from backendcode.celery_config import celery_app
from backendcode.utils import extract_video_id

from backendcode.data_models import EnvironmentVariablesConfig

config = EnvironmentVariablesConfig()

# the redis client used to ping the redis server
redis_ping_client = redis.Redis(host=config.redis_address, port=config.redis_port, db=0, socket_timeout=10)

def get_redis_fetch_client():
    config = EnvironmentVariablesConfig()
    return redis.Redis(host=config.redis_address, port=config.redis_port, db=1)

app = FastAPI()
# For security, we only allow the origin we specify to interact with the backend. 
# Thus, any frontend with a different origin is not allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.origin_address],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

THUMBNAIL_DIR = config.fullpath_thumbnails
VIDEOS_DIR = config.fullpath_videos
os.makedirs(THUMBNAIL_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)
app.mount("/thumbnails", StaticFiles(directory=THUMBNAIL_DIR), name="thumbnails")
app.mount("/videos", StaticFiles(directory=VIDEOS_DIR), name="videos")

def get_redis_ping_client():
    """ Create a new Redis client if the current one is disconnected. """
    global redis_ping_client
    try:
        if redis_ping_client is None or not redis_ping_client.ping():  # Check if Redis is alive
            redis_ping_client = redis.Redis(host=config.redis_address, port=config.redis_port, db=0, socket_timeout=10)
        return redis_ping_client
    except redis.ConnectionError:
        return None  # Return None if Redis is unreachable

def is_celery_available() -> bool:

    """Check if Celery workers are running.

    Returns:
        bool: True if Celery workers are running, False otherwise.
    """
    inspect = celery_app.control.inspect()

    if inspect and inspect.ping():
        return True  
    return False  


def is_redis_available():
    """ Check if Redis is available and reconnect if needed. """
    client = get_redis_ping_client()
    return client.ping() if client else False

@app.get("/video")
def submit_video_url(url: str):

    """
    Submit a YouTube video URL to be processed.

    Args:
        url (str): The YouTube video URL.

    Returns:
        dict: A JSON object containing the task ID and status.
    """
    
    # Check if Redis and Celery are available to execute tasks
    if not is_redis_available() or not is_celery_available():
        raise HTTPException(status_code=503, detail="Task processing service is unavailable.")
    
    # Extract the video ID from the URL
    videoID =""
    try:
        videoID = extract_video_id(url)
    except Exception:
        raise HTTPException(status_code=400, detail="URL is not formatted properly. Please ensure your using a valid YouTube video URL.")
    actualURL = f"https://www.youtube.com/watch?v={videoID}"

    # Schedule the task for execution by celery and return the task ID to the client
    try:
        task = extract_info.apply_async(args=[actualURL], expires=30)
        return {"task_id": task.id, "status": "processing"}
    except Exception:
        raise HTTPException(status_code=503, detail="Failed to connect to task scheduling service.")

@app.get("/video/{task_id}")
def get_video_format_data(task_id: str):

    """
    Get the status and the format data result of a video by task ID.

    Args:
        task_id (str): The ID of the task to retrieve.

    Returns:
        dict: A JSON object containing the task ID, status, and result (if available).
    """

    task = celery_app.AsyncResult(task_id)
    if task.state == "PENDING":
        return {"task_id": task_id, "status": "pending"}
    elif task.state == "SUCCESS":
        return {"task_id": task_id, "status": "completed", "result": strip_required_data(task.result)}
    elif task.state == "FAILURE" or task.state =="REVOKED" or task.state == "RETRY":
        return {"task_id": task_id, "status": "retry", "error": str(task.result)}
    else:
        return {"task_id": task_id, "status": task.state.lower()}

@app.get("/video/thumbnail/{task_id}")
async def get_thumbnail(task_id: str):
    """
    Retrieve the thumbnail image for a video processing task.

    Args:
        task_id (str): The ID of the task to retrieve the thumbnail for.

    Returns:
        dict: A JSON object containing:
            - "task_id": The ID of the task.
            - "status": The current task status ("processing", "success", "retry", or other states).
            - "image_url": (only if the task is successful) The URL of the downloaded thumbnail image.
            - "error": (only if the task has failed, been revoked, or is in a retry state) The error message.
    """

    task = celery_app.AsyncResult(task_id)
    if task.state == "PENDING":
        return {"task_id": task_id, "status": "processing"}
    elif task.state == "SUCCESS":

        thumnailURL = (task.result).get('thumbnail',None)
        path = await download_image(thumnailURL, f"{task_id}")
        image_url = f"/thumbnails/{Path(path).name}"
        delete_thumbnail.apply_async(args=[task_id], countdown=config.thumbnail_persistence_duration)

        return {"task_id": task_id, "status": "success", "image_url": image_url}
    
    elif task.state == "FAILURE" or task.state =="REVOKED" or task.state == "RETRY":
        return {"task_id": task_id, "status": "retry", "error": str(task.result)}
    else:
        return {"task_id": task_id, "status": task.state}

async def download_image(url: str, filename: str) -> str:
    """Asynchronously download an image and save it with the correct extension."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to download image")

        extension = await get_image_extension(url, response.headers)
        full_filename = f"{filename}{extension}"
        file_path = os.path.join(THUMBNAIL_DIR,full_filename)

        with open(file_path, "wb") as f:
            f.write(response.content)

    return str(file_path)

async def get_image_extension(url: str, response_headers) -> str:
    """Determine the image extension from the URL or Content-Type header."""
    content_type = response_headers.get("content-type")
    if content_type:
        ext = mimetypes.guess_extension(content_type)
        if ext:
            return ext

    parsed_url = urlparse(url)
    path = parsed_url.path
    ext = Path(path).suffix
    if ext.lower() in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
        return ext

    raise HTTPException(status_code=400, detail="Could not determine image extension")


@app.get("/video/download/{task_id}")
def full_details(task_id: str):
    """Check task status and fetch results."""
    task = celery_app.AsyncResult(task_id)
    if task.state == "PENDING":
        return {"task_id": task_id, "status": "processing"}
    elif task.state == "SUCCESS":
        return {"task_id": task_id, "status": "completed", "result": (task.result)}
    elif task.state == "FAILURE":
        return {"task_id": task_id, "status": "failed", "error": str(task.result)}
    else:
        return {"task_id": task_id, "status": task.state}


@app.websocket("/video/download")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        data = await websocket.receive_json()

        video_format = data["format"]
        task_id = data["task_id"]
        
        # Check if the task ID is valid
        if(celery_app.AsyncResult(task_id).result is None):
            raise Exception("Invalid task ID/Too soon to make a request.")
        
        # Get the result URL of the video 
        url = celery_app.AsyncResult(task_id).result.get("original_url", None)

        # Schedule the download task. This is to be run in the background by celery.
        task = download_video.apply_async(args=[task_id, url, video_format])

        # Create a new redis client for each websocket request to avoid collision issues
        redis_client = get_redis_fetch_client() 
        while not task.ready():

            # We look if there are any updates for our task id
            if redis_client.scan_iter(f"{task_id}:*"):
                
                # If there are updates, we send them to the client
                value = redis_client.get(f"{task_id}:progress")
                downloadStatus = redis_client.get(f"{task_id}:status")
                if value is not None:
                    value = value.decode()
                    downloadStatus = downloadStatus.decode('utf-8')

                    await websocket.send_json({"status": downloadStatus,"progress": value})
            # Sleep for 2 seconds
            await asyncio.sleep(2)

        # Finally, when the task is completed, we update the status.
        await websocket.send_json({"status": "completed", 
                                   "message": "Video download finished!",
                                   "URL":redis_client.get(task_id+":path").decode('utf-8')})
    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(e)
        await websocket.send_json({"status": "error", "message": str(e)})   
    finally:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1000)
            print("WebSocket closed.")
        else:
            print(f"WebSocket state: {websocket.client_state}")


def strip_required_data(info):
    """Fetch video formats and metadata, return it as a dictionary."""
    formats = info.get('formats', [])
    return {
        "name": info.get('title', 'Unknown'),
        "duration_string": info.get('duration_string', 'N/A'),
        "formats": [
            {
                'format_id': fmt.get('format_id', 'N/A'),
                'ext': fmt.get('ext', 'N/A'),
                'vcodec': fmt.get('vcodec', 'N/A'),
                'resolution': fmt.get('resolution', 'N/A'),
                "fps": fmt.get('fps', 'N/A'),
                "filesize": fmt.get('filesize', 'N/A')
            }
            for fmt in formats
        ]
    }


@app.get("/video/details/{task_id}")
def get_detailed_video_format_data(task_id: str):

    """
    Retrieve detailed information about a video processing task.

    Args:
        task_id (str): The ID of the task to retrieve details for.

    Returns:
        dict: A JSON object containing the task ID, status, and result (if available).
              - If the task is pending, returns the status as "pending".
              - If the task is completed successfully, returns the status as "completed" with the result.
              - If the task has failed, been revoked, or is in a retry state, returns the status as "retry" with the error message.
              - Otherwise, returns the current task status in lowercase.
    """

    task = celery_app.AsyncResult(task_id)
    if task.state == "PENDING":
        return {"task_id": task_id, "status": "pending"}
    elif task.state == "SUCCESS":
        return {"task_id": task_id, "status": "completed", "result": (task.result)}
    elif task.state == "FAILURE" or task.state =="REVOKED" or task.state == "RETRY":
        return {"task_id": task_id, "status": "retry", "error": str(task.result)}
    else:
        return {"task_id": task_id, "status": task.state.lower()}