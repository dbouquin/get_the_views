"""
YouTube Video Metrics Collector

This script reads a CSV containing YouTube video URLs and retrieves 
metrics for each video using the YouTube Data API v3. It outputs a new CSV
with comprehensive video statistics.

Requirements:
    - google-api-python-client
    - pandas

Install with: conda install -c conda-forge google-api-python-client pandas
"""

import csv
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# ============================================================================
# CONFIGURATION
# ============================================================================

# File paths
API_KEY_FILE = "youtube_api_key.txt"
INPUT_CSV = "2025_video_links.csv"
# Get date for output file name
from datetime import datetime
current_date = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_CSV = f"results/youtube_metrics_output_{current_date}.csv"


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
# URL PARSING FUNCTIONS
# ============================================================================

def extract_video_id(url: str) -> Optional[str]:
    """
    Extract the video ID from a YouTube URL.
    
    Handles multiple YouTube URL formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    - https://youtu.be/VIDEO_ID
    
    Args:
        url: The YouTube URL to parse
        
    Returns:
        The video ID as a string, or None if the URL format is not recognized
    """
    # Handle /shorts/ format
    shorts_match = re.search(r'/shorts/([a-zA-Z0-9_-]+)', url)
    if shorts_match:
        return shorts_match.group(1)
    
    # Handle youtu.be format
    if 'youtu.be/' in url:
        parsed = urlparse(url)
        video_id = parsed.path.strip('/')
        return video_id if video_id else None
    
    # Handle /watch?v= format
    if 'youtube.com/watch' in url:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        return query_params.get('v', [None])[0]
    
    return None


# ============================================================================
# YOUTUBE API FUNCTIONS
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
            # Request video details
            # 'snippet' contains title, channel, upload date
            # 'statistics' contains view count, likes, comments
            # 'contentDetails' contains duration
            response = youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(batch)
            ).execute()
            
            # Process each video in the response
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
            
            # Check for videos that weren't returned (deleted, private, etc.)
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
            # Handle API errors (quota exceeded, invalid key, etc.)
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
# CSV PROCESSING FUNCTIONS
# ============================================================================

def read_input_csv(filename: str) -> List[Dict[str, str]]:
    """
    Read the input CSV containing nicknames and video URLs.
    
    Args:
        filename: Path to the input CSV file
        
    Returns:
        List of dictionaries, each containing 'nickname' and 'url' keys
    """
    videos = []
    
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Handle different possible column name formats in the input CSV
            nickname = row.get('Nickname') or row.get('nickname')
            link = row.get('Link') or row.get('link') or row.get('URL') or row.get('url')
            
            if link:
                videos.append({
                    'nickname': nickname or 'N/A',
                    'url': link.strip()
                })
    
    return videos


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
    
    # Define the column order for the output CSV
    fieldnames = [
        'nickname',
        'title',
        'channel_name',
        'upload_date',
        'url',
        'video_id',
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
    2. Read input CSV with video URLs
    3. Extract video IDs from URLs
    4. Retrieve metrics from YouTube API
    5. Combine all data
    6. Write output CSV
    """
    # Load API key from file
    print(f"Loading API key from: {API_KEY_FILE}")
    try:
        API_KEY = read_api_key(API_KEY_FILE)
        print("API key loaded successfully")
    except (FileNotFoundError, ValueError) as e:
        return
    
    print(f"\nReading input file: {INPUT_CSV}")
    videos = read_input_csv(INPUT_CSV)
    print(f"Found {len(videos)} videos to process")
    
    # Extract video IDs and create a mapping
    video_id_map = {}  # Maps video_id to the original video data
    video_ids = []
    
    for video in videos:
        video_id = extract_video_id(video['url'])
        if video_id:
            video_ids.append(video_id)
            video_id_map[video_id] = video
        else:
            print(f"Warning: Could not extract video ID from URL: {video['url']}")
    
    print(f"Successfully extracted {len(video_ids)} video IDs")
    
    if not video_ids:
        print("No valid video IDs found. Exiting.")
        return
    
    # Retrieve metrics from YouTube API
    print(f"Retrieving metrics from YouTube API...")
    metrics = get_video_metrics(video_ids, API_KEY)
    print(f"Retrieved metrics for {len(metrics)} videos")
    
    # Combine original data with metrics
    output_data = []
    for video_id, video_metrics in metrics.items():
        original_data = video_id_map.get(video_id, {})
        
        combined_row = {
            'nickname': original_data.get('nickname', 'N/A'),
            'title': video_metrics['title'],
            'channel_name': video_metrics['channel_name'],
            'upload_date': video_metrics['upload_date'],
            'url': original_data.get('url', 'N/A'),
            'video_id': video_id,
            'view_count': video_metrics['view_count'],
            'like_count': video_metrics['like_count'],
            'comment_count': video_metrics['comment_count'],
            'duration': video_metrics['duration'],
            'error': video_metrics['error'] or ''
        }
        
        output_data.append(combined_row)

    # Sort by upload date for easier reading
    output_data.sort(key=lambda x: x['upload_date'])

    # Write output CSV
    print(f"Writing output file: {OUTPUT_CSV}")
    write_output_csv(OUTPUT_CSV, output_data)
    
    # Print summary statistics
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    total_views = sum(int(row['view_count']) for row in output_data if row['view_count'].isdigit())
    print(f"Total videos processed: {len(output_data)}")
    print(f"Total views across all videos: {total_views:,}")
    
    errors = [row for row in output_data if row['error']]
    if errors:
        print(f"\nVideos with errors: {len(errors)}")
        for row in errors:
            print(f"  - {row['nickname']}: {row['error']}")


if __name__ == "__main__":
    main()