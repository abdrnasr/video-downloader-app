from urllib.parse import urlparse, parse_qs
from fastapi import HTTPException
import re

def extract_video_id(url: str) -> str:
    """
    Extract the YouTube video ID from a given URL.

    This function attempts to extract the video ID from a YouTube URL by first
    checking the query string for the "v" parameter. If the parameter is not
    present, it will try to extract the ID from the URL path, which may be in
    formats like youtu.be/<id> or embed/<id>.

    Args:
        url (str): The YouTube video URL.

    Returns:
        str: The extracted YouTube video ID.

    Raises:
        HTTPException: If the URL is not formatted properly or does not contain
                       a valid YouTube video ID.
    """

    try:
        parsed_url = urlparse(url)
        
        # Case 1: Check query string (v=...)
        query_params = parse_qs(parsed_url.query)
        video_id = query_params.get("v")
        if video_id:
            videoID = video_id[0]
        else:
            # Case 2: Try to extract from path (e.g., youtu.be/<id> or embed/<id>)
            pattern = r"(?:\/|^)([0-9A-Za-z_-]{11})(?:\?|$)"
            match = re.search(pattern, parsed_url.path)
            if match:
                videoID = match.group(1)
            else:
                raise ValueError
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="URL is not formatted properly. Please ensure you're using a valid YouTube video URL."
        )
    
    return videoID