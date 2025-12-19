# YouTube Video Metrics Collector

A Python script that retrieves detailed metrics for YouTube videos using the YouTube Data API v3. 

## What This Script Does

Given a CSV file containing YouTube video URLs, this script will:
- Extract video IDs from various YouTube URL formats (standard videos, Shorts, and livestreams)
- Retrieve comprehensive metrics from the YouTube Data API
- Generate a CSV report with video titles, view counts, likes, comments, etc.
- Preserve video nicknames for easy reference

## Prerequisites

- A Google account
- YouTube Data API v3 access (free, instructions below)

## Setup Instructions

### Step 1: Get Your YouTube Data API Key

1. **Go to Google Cloud Console**  
   Visit [https://console.cloud.google.com/](https://console.cloud.google.com/)

2. **Create a new project**
   - Click the project dropdown at the top of the page
   - Click "New Project"
   - Name it something (e.g., "DevRel YouTube Analytics")
   - Click "Create"

3. **Enable the YouTube Data API v3**
   - Use the search bar at the top and type "YouTube Data API v3"
   - Click on it in the results
   - Click the "Enable" button

4. **Create an API key**
   - Click "Create Credentials" in the top right
   - Select "API key"
   - Your key will be generated and displayed
   - **Important**: Click "Restrict Key" and set it to only work with YouTube Data API v3 
   - Copy your API key

5. **Save your API key**
   - Create a file named `youtube_api_key.txt` in the same directory as your script
   - Paste your API key into the file (just the key, nothing else)
   - Save the file

### Step 2: Create an Environment and Install Required Libraries

```bash
conda create -name youtube_counts python=3.13
conda activate youtube_counts
conda install -c conda-forge google-api-python-client pandas -y
```

### Step 3: Prepare Your Input File

Create a CSV file named `2025_video_links.csv` (or modify the filename in the script) with the following format:

```csv
nickname,url
My Tutorial,https://www.youtube.com/watch?v=VIDEO_ID
Short Demo,https://www.youtube.com/shorts/VIDEO_ID
```

The script handles multiple URL formats:
- Standard videos: `https://www.youtube.com/watch?v=VIDEO_ID`
- YouTube Shorts: `https://www.youtube.com/shorts/VIDEO_ID`
- Short URLs: `https://youtu.be/VIDEO_ID`

## Running the Script

Once everything is set up, run:

```bash
python youtube_metrics_collector.py
```

The script will:
1. Load your API key from `youtube_api_key.txt`
2. Read your video URLs from `2025_video_links.csv`
3. Retrieve metrics from YouTube
4. Generate `results/youtube_metrics_output_{current_date}.csv` with all the data
5. Display a summary of total videos processed and combined view counts

## Output Format

The output CSV will contain the following columns:

- **nickname**: Your custom name for the video
- **title**: The actual video title from YouTube
- **channel_name**: The channel that posted the video
- **upload_date**: When the video was published (ISO format)
- **url**: The original URL from your input file
- **video_id**: The extracted video ID
- **view_count**: Total number of views
- **like_count**: Total number of likes
- **comment_count**: Total number of comments
- **duration**: Video length (in ISO 8601 format, e.g., PT3M24S = 3 minutes 24 seconds)
- **error**: Any error message if the video couldn't be retrieved

## API Quota Information

The YouTube Data API v3 has a free tier with a daily quota of 10,000 units. Each video lookup costs 1 unit, so you can check thousands of videos per day without charges.

## File Structure

```
your-project/
├── youtube_metrics_collector.py                    # Main script
├── youtube_api_key.txt                             # Your API key 
├── 2025_video_links.csv                            # Input file with video URLs
└── results/                                        # Directory for output files
    └── youtube_metrics_output_{current_date}.csv   # Generated output file
├── .gitignore                                      # Prevents committing sensitive files
└── README.md                                       # This file
```

## Security Note

Never commit your `youtube_api_key.txt` file to version control! The included `.gitignore` file already excludes it, but always double-check before pushing to GitHub or sharing your code.