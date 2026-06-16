"""
YouTube Channel Metrics Collector

This script retrieves all videos from a YouTube channel and their metrics
using the YouTube Data API v3. Results can be filtered by date range.

Requirements:
    - google-api-python-client
    - pandas (optional, for easier date filtering)

Install with: conda install -c conda-forge google-api-python-client pandas
"""

import csv
import re
from typing import Dict, List, Optional
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# ============================================================================
# CONFIGURATION
# ============================================================================

# File paths
API_KEY_FILE = "youtube_api_key.txt"

# Channel ID or username to fetch videos from
# You can find the channel ID from the channel URL:
# - https://www.youtube.com/channel/CHANNEL_ID
# - https://www.youtube.com/@username (use the username without @)
CHANNEL_ID = ""  # Leave empty to use username instead
# OR use channel username (without @)
CHANNEL_USERNAME = "AnacondaInc."  # From https://www.youtube.com/@AnacondaInc./

# Optional: Filter by date range (format: YYYY-MM-DD)
# Leave as None to fetch all videos
START_DATE = None  # e.g., "2026-01-01"
END_DATE = None    # e.g., "2026-03-31"

# Maximum number of videos to retrieve (None = all videos)
MAX_VIDEOS = None

# Output file
current_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_CSV = f"results/channel_metrics_output_{current_timestamp}.csv"


def read_api_key(filename: str) -> str:
    """
    Read the YouTube Data API key from a text file.

    The file should contain only the API key with no extra formatting.
    Leading and trailing whitespace will be automatically removed.

    Args:
        filename: Path to the file containing the API key

    Returns:
        The API key as a string

    Raises:
        FileNotFoundError: If the API key file doesn't exist
        ValueError: If the API key file is empty
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            api_key = f.read().strip()

        if not api_key:
            raise ValueError(f"API key file '{filename}' is empty")

        return api_key

    except FileNotFoundError:
        print(f"\nError: API key file '{filename}' not found.")
        print("Please create this file and add your YouTube Data API v3 key to it.")
        print("The file should contain only your API key with no extra text.\n")
        raise


# ============================================================================
# YOUTUBE API FUNCTIONS - CHANNEL
# ============================================================================

def get_channel_id_from_username(username: str, api_key: str) -> Optional[str]:
    """
    Convert a channel username to a channel ID.

    Args:
        username: YouTube channel username (without @)
        api_key: YouTube Data API v3 key

    Returns:
        Channel ID or None if not found
    """
    youtube = build('youtube', 'v3', developerKey=api_key)

    try:
        response = youtube.channels().list(
            part='id',
            forUsername=username
        ).execute()

        items = response.get('items', [])
        if items:
            return items[0]['id']

        # Try searching by handle
        response = youtube.search().list(
            part='snippet',
            q=f'@{username}',
            type='channel',
            maxResults=1
        ).execute()

        items = response.get('items', [])
        if items:
            return items[0]['snippet']['channelId']

    except HttpError as e:
        print(f"Error looking up channel: {e}")

    return None


def get_channel_videos(channel_id: str, api_key: str, max_results: Optional[int] = None) -> List[str]:
    """
    Retrieve all video IDs from a YouTube channel.

    Args:
        channel_id: YouTube channel ID
        api_key: YouTube Data API v3 key
        max_results: Maximum number of videos to retrieve (None = all)

    Returns:
        List of video IDs
    """
    youtube = build('youtube', 'v3', developerKey=api_key)
    video_ids = []

    try:
        # First, get the 'uploads' playlist ID for the channel
        channel_response = youtube.channels().list(
            part='contentDetails',
            id=channel_id
        ).execute()

        if not channel_response.get('items'):
            print(f"Error: Channel {channel_id} not found")
            return []

        uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # Retrieve all videos from the uploads playlist
        next_page_token = None

        while True:
            playlist_response = youtube.playlistItems().list(
                part='contentDetails',
                playlistId=uploads_playlist_id,
                maxResults=50,  # API maximum
                pageToken=next_page_token
            ).execute()

            for item in playlist_response.get('items', []):
                video_id = item['contentDetails']['videoId']
                video_ids.append(video_id)

                if max_results and len(video_ids) >= max_results:
                    return video_ids

            next_page_token = playlist_response.get('nextPageToken')

            if not next_page_token:
                break

    except HttpError as e:
        print(f"Error retrieving videos: {e}")

    return video_ids


# ============================================================================
# YOUTUBE API FUNCTIONS - VIDEO METRICS
# ============================================================================

def get_video_metrics(video_ids: List[str], api_key: str) -> Dict[str, Dict]:
    """
    Retrieve metrics for a list of YouTube videos using the YouTube Data API.

    The API allows up to 50 video IDs per request, so this function handles
    batching automatically if needed.

    Args:
        video_ids: List of YouTube video IDs to retrieve metrics for
        api_key: YouTube Data API v3 key

    Returns:
        Dictionary mapping video IDs to their metrics. Each metrics dictionary
        contains: title, channel_name, upload_date, view_count, like_count,
        comment_count, duration, and an error field if the request failed.
    """
    youtube = build('youtube', 'v3', developerKey=api_key)

    results = {}

    # The API allows up to 50 IDs per request
    batch_size = 50
    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i:i + batch_size]

        try:
            response = youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(batch)
            ).execute()

            for item in response.get('items', []):
                video_id = item['id']
                snippet = item['snippet']
                statistics = item.get('statistics', {})
                content_details = item.get('contentDetails', {})

                results[video_id] = {
                    'title': snippet.get('title', 'N/A'),
                    'channel_name': snippet.get('channelTitle', 'N/A'),
                    'upload_date': snippet.get('publishedAt', 'N/A'),
                    'view_count': statistics.get('viewCount', '0'),
                    'like_count': statistics.get('likeCount', '0'),
                    'comment_count': statistics.get('commentCount', '0'),
                    'duration': content_details.get('duration', 'N/A'),
                    'error': None
                }

            returned_ids = {item['id'] for item in response.get('items', [])}
            for video_id in batch:
                if video_id not in returned_ids:
                    results[video_id] = {
                        'title': 'N/A',
                        'channel_name': 'N/A',
                        'upload_date': 'N/A',
                        'view_count': '0',
                        'like_count': '0',
                        'comment_count': '0',
                        'duration': 'N/A',
                        'error': 'Video not found (may be deleted or private)'
                    }

        except HttpError as e:
            error_message = f"API Error: {e.resp.status} - {e.content.decode()}"
            print(f"Error retrieving batch: {error_message}")

            for video_id in batch:
                if video_id not in results:
                    results[video_id] = {
                        'title': 'N/A',
                        'channel_name': 'N/A',
                        'upload_date': 'N/A',
                        'view_count': '0',
                        'like_count': '0',
                        'comment_count': '0',
                        'duration': 'N/A',
                        'error': error_message
                    }

    return results


# ============================================================================
# DATE FILTERING
# ============================================================================

def filter_by_date(data: List[Dict], start_date: Optional[str] = None,
                  end_date: Optional[str] = None) -> List[Dict]:
    """
    Filter video data by upload date range.

    Args:
        data: List of video dictionaries
        start_date: Start date in YYYY-MM-DD format (inclusive)
        end_date: End date in YYYY-MM-DD format (inclusive)

    Returns:
        Filtered list of videos
    """
    if not start_date and not end_date:
        return data

    filtered = []

    for video in data:
        upload_date_str = video['upload_date']

        if upload_date_str == 'N/A':
            continue

        try:
            # Parse ISO 8601 format (YouTube API format)
            upload_date = datetime.fromisoformat(upload_date_str.replace('Z', '+00:00'))
            upload_date = upload_date.date()

            # Check date range
            if start_date:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                if upload_date < start:
                    continue

            if end_date:
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                if upload_date > end:
                    continue

            filtered.append(video)

        except (ValueError, AttributeError) as e:
            print(f"Warning: Could not parse date '{upload_date_str}': {e}")
            continue

    return filtered


# ============================================================================
# CSV OUTPUT
# ============================================================================

def write_output_csv(filename: str, data: List[Dict[str, str]]):
    """
    Write the collected metrics to an output CSV file.

    Args:
        filename: Path to the output CSV file
        data: List of dictionaries containing all video data and metrics
    """
    if not data:
        print("No data to write.")
        return

    fieldnames = [
        'video_id',
        'title',
        'channel_name',
        'upload_date',
        'url',
        'view_count',
        'like_count',
        'comment_count',
        'duration',
        'error'
    ]

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"Successfully wrote {len(data)} rows to {filename}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Main execution function that orchestrates the full process.

    Steps:
    1. Load API key from file
    2. Resolve channel ID (from ID or username)
    3. Retrieve all video IDs from the channel
    4. Retrieve metrics for each video
    5. Filter by date range if specified
    6. Write output CSV
    """
    print(f"Loading API key from: {API_KEY_FILE}")
    try:
        API_KEY = read_api_key(API_KEY_FILE)
        print("API key loaded successfully")
    except (FileNotFoundError, ValueError):
        return

    # Resolve channel ID
    channel_id = CHANNEL_ID

    if not channel_id and CHANNEL_USERNAME:
        print(f"\nResolving channel ID for username: {CHANNEL_USERNAME}")
        channel_id = get_channel_id_from_username(CHANNEL_USERNAME, API_KEY)
        if not channel_id:
            print("Error: Could not resolve channel ID from username")
            return
        print(f"Found channel ID: {channel_id}")

    if not channel_id:
        print("\nError: No channel ID or username specified")
        print("Please set CHANNEL_ID or CHANNEL_USERNAME in the script configuration")
        return

    # Retrieve all video IDs from the channel
    print(f"\nRetrieving videos from channel: {channel_id}")
    video_ids = get_channel_videos(channel_id, API_KEY, MAX_VIDEOS)
    print(f"Found {len(video_ids)} videos")

    if not video_ids:
        print("No videos found. Exiting.")
        return

    # Retrieve metrics for all videos
    print(f"\nRetrieving metrics from YouTube API...")
    metrics = get_video_metrics(video_ids, API_KEY)
    print(f"Retrieved metrics for {len(metrics)} videos")

    # Combine data
    output_data = []
    for video_id, video_metrics in metrics.items():
        combined_row = {
            'video_id': video_id,
            'title': video_metrics['title'],
            'channel_name': video_metrics['channel_name'],
            'upload_date': video_metrics['upload_date'],
            'url': f"https://www.youtube.com/watch?v={video_id}",
            'view_count': video_metrics['view_count'],
            'like_count': video_metrics['like_count'],
            'comment_count': video_metrics['comment_count'],
            'duration': video_metrics['duration'],
            'error': video_metrics['error'] or ''
        }
        output_data.append(combined_row)

    # Filter by date if specified
    if START_DATE or END_DATE:
        print(f"\nFiltering by date range: {START_DATE or 'beginning'} to {END_DATE or 'now'}")
        output_data = filter_by_date(output_data, START_DATE, END_DATE)
        print(f"After filtering: {len(output_data)} videos")

    # Sort by upload date
    output_data.sort(key=lambda x: x['upload_date'])

    # Write output CSV
    print(f"\nWriting output file: {OUTPUT_CSV}")
    write_output_csv(OUTPUT_CSV, output_data)

    # Print summary statistics
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    total_views = sum(int(row['view_count']) for row in output_data if row['view_count'].isdigit())
    total_likes = sum(int(row['like_count']) for row in output_data if row['like_count'].isdigit())
    total_comments = sum(int(row['comment_count']) for row in output_data if row['comment_count'].isdigit())

    print(f"Total videos processed: {len(output_data)}")
    print(f"Total views: {total_views:,}")
    print(f"Total likes: {total_likes:,}")
    print(f"Total comments: {total_comments:,}")

    if output_data:
        avg_views = total_views / len(output_data)
        print(f"Average views per video: {avg_views:,.1f}")

    errors = [row for row in output_data if row['error']]
    if errors:
        print(f"\nVideos with errors: {len(errors)}")
        for row in errors[:5]:
            print(f"  - {row['title']}: {row['error']}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")


if __name__ == "__main__":
    main()
