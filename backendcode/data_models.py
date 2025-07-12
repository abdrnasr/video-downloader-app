import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()


# This is the configuration for the environment variables, keeping it centralized
class EnvironmentVariablesConfig:
    _instance = None

    # Type hints for the fields
    origin_address: str
    redis_address: str
    redis_port: int

    # Optional relative/absolute path provided by the user
    thumbnail_path: str
    video_path: str

    # Full absolute paths resolved by the system
    fullpath_thumbnails: str
    fullpath_videos: str
    
    # The amount of time to wait before deleting thumbnails and videos
    thumbnail_persistence_duration: int
    video_persistence_duration: int

    def __new__(cls) -> "EnvironmentVariablesConfig":
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        self.origin_address = os.getenv("FRONT_END_ORIGIN")
        self.redis_address = os.getenv("REDIS_ADDRESS")
        redis_port_str = os.getenv("REDIS_PORT")

        # Optionals with defaults
        self.thumbnail_path = os.getenv("THUMBNAIL_PATH", "thumbnails")
        self.video_path = os.getenv("VIDEO_PATH", "videos")

        # Validate the types of Environment Variables
        try:
            self.thumbnail_persistence_duration = int(os.getenv("THUMBNAIL_PERSISTANCE_DURATION", 600))
        except ValueError:
            raise ValueError("Environment variable THUMBNAIL_PERSISTANCE_DURATION must be an integer.")
        
        try:
            self.video_persistence_duration = int(os.getenv("VIDEO_PERSISTANCE_DURATION", 3600))
        except ValueError:
            raise ValueError("Environment variable VIDEO_PERSISTANCE_DURATION must be an integer.")

        # Resolve to full absolute paths if relative
        self.fullpath_thumbnails = (
            str(Path(self.thumbnail_path).resolve()) if not os.path.isabs(self.thumbnail_path) else self.thumbnail_path
        )

        self.fullpath_videos = (
            str(Path(self.video_path).resolve()) if not os.path.isabs(self.video_path) else self.video_path
        )

        if not self.origin_address:
            raise ValueError("Environment variable FRONT_END_ORIGIN is missing or empty.")
        if not self.redis_address:
            raise ValueError("Environment variable REDIS_ADDRESS is missing or empty.")
        if not redis_port_str:
            raise ValueError("Environment variable REDIS_PORT is missing or empty.")

        try:
            self.redis_port = int(redis_port_str)
        except ValueError:
            raise ValueError("Environment variable REDIS_PORT must be an integer.")

    def __repr__(self):
        return (f"EnvironmentVariablesConfig(origin_address={self.origin_address}, "
                f"redis_address={self.redis_address}, redis_port={self.redis_port}, "
                f"fullpath_thumbnails={self.fullpath_thumbnails}, fullpath_videos={self.fullpath_videos}, "
                f"thumbnail_persistence_duration={self.thumbnail_persistence_duration}, "
                f"video_persistence_duration={self.video_persistence_duration})")
