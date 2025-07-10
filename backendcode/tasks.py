from backendcode.celery_config import celery_app
import yt_dlp
import os
import redis
import time
import shutil

from backendcode.data_models import EnvironmentVariablesConfig
config = EnvironmentVariablesConfig()

def get_redis_client():
    config = EnvironmentVariablesConfig()
    return redis.Redis(host=config.redis_address, port=config.redis_port, db=1)

@celery_app.task
def extract_info(url):
    """Fetch video metadata using yt-dlp."""
    ydl_opts = {'quiet': True, 'listformats': False}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

@celery_app.task(bind=True)
def download_video(self,task_id, url, video_format, client_id):

    # Test if a connection could be established with redis
    redis_client = get_redis_client()
    try:
        redis_client.ping()
    except redis.exceptions.RedisError as e:
        print(f"Redis connection failed: {e}")
        raise

    # Define a progress hook that keep redis updated with the download status
    def progress_hook(d):
        if d['status'] == 'downloading':
            redis_client.set(task_id+":eta",d['_eta_str'])
            redis_client.set(task_id+":speed",d['_speed_str'])
            redis_client.set(task_id+":progress",d['_percent_str'])
            redis_client.set(task_id+":status","downloading")
        elif d['status'] == 'finished':
            redis_client.set(task_id+":status","finished")
            time.sleep(2)

    # Ensure the video directory exists and create a folder for the task_id
    output_directory = config.fullpath_videos
    task_directory = os.path.join(output_directory, task_id)
    os.makedirs(task_directory, exist_ok=True)

    # Define the path to store the video at along with its name
    video_Path = os.path.join(task_directory, '%(title)s.%(ext)s')

    # Define the download options for yt-dlp
    ydl_opts = {
        'format': f"{video_format}+ba[ext!=webm]",  # Select the format and best audio
        'progress_hooks': [progress_hook],  # Hook for live updates
        'outtmpl': video_Path,
        "keepvideo": False,
        "merge_output_format": "mp4"
    }
    
    # start the download procedure
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Since we do not know in advance the extension of the file is, and there will only be one file in the directory, 
    # we can just get the first file
    file_names = [f for f in os.listdir(task_directory) if os.path.isfile(os.path.join(task_directory, f))]

    # This the URL that the user will navigate to download the video.
    redis_client.set(f"{task_id}:path",f"/videos/{task_id}/{file_names[0]}")

    # Schedule a video deletion task to be completed later
    delete_video_folder.apply_async(args=[task_id], countdown=config.video_persistence_duration)

    return {"status": "completed", "message": "Video download finished!"}


@celery_app.task
def delete_thumbnail(task_id: str):

    # Finds the thumbnail image in the thumbnail directory and delete the one that matches the task_id
    thumb_directory = config.fullpath_thumbnails
    for file in os.listdir(thumb_directory):
        full_path = os.path.join(thumb_directory, file)
        if os.path.isfile(full_path) and task_id in file:
            os.remove(full_path)
            print(f"Deleted thumbnail: {full_path}")
            return
    print(f"Thumbnail not found: {full_path}")


@celery_app.task
def delete_video_folder(task_id: str):

    # Build the path to the video directory of the task_id
    video_output_directory = config.fullpath_videos
    video_task_directory = os.path.join(video_output_directory, task_id)

    # Delete the folder 
    if os.path.exists(video_task_directory) and os.path.isdir(video_task_directory):
        shutil.rmtree(video_task_directory)
        print( f"Deleted: {video_task_directory}")
    else:
        print( f"Folder not found: {video_task_directory}")