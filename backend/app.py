#!/usr/bin/env python3
"""
Robust Video Extractor with TikTok-specific handling
Includes fallback methods and better error handling
"""

import os
import sys
import json
import time
import uuid
import threading
import requests
import re
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging
import yt_dlp
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app, origins=["*"])
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Global variables
active_downloads = {}

class RobustVideoExtractor:
    """Enhanced video extractor with TikTok-specific handling and fallbacks"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        })
        
        # Base yt-dlp options
        self.base_options = {
            'quiet': False,
            'no_warnings': False,
            'extractaudio': False,
            'format': 'best[height<=1080]',
            'nocheckcertificate': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive'
            },
            'retries': 10,
            'fragment_retries': 10,
            'socket_timeout': 60,
            'extractor_retries': 5
        }
        
        # TikTok specific options
        self.tiktok_options = self.base_options.copy()
        self.tiktok_options.update({
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }
        })

    def detect_platform(self, url):
        """Detect video platform with better TikTok detection"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # TikTok detection (including mobile and short URLs)
            if any(d in domain for d in ['tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com']):
                return 'tiktok'
            elif any(d in domain for d in ['douyin.com', 'v.douyin.com', 'iesdouyin.com']):
                return 'douyin'
            elif any(d in domain for d in ['youtube.com', 'youtu.be', 'm.youtube.com', 'youtube-nocookie.com']):
                return 'youtube'
            elif any(d in domain for d in ['instagram.com', 'instagr.am']):
                return 'instagram'
            elif any(d in domain for d in ['facebook.com', 'fb.watch', 'm.facebook.com', 'fb.com']):
                return 'facebook'
            else:
                return 'unknown'
        except:
            return 'unknown'

    def resolve_tiktok_url(self, url):
        """Resolve TikTok short URLs to full URLs"""
        try:
            if 'vm.tiktok.com' in url or 'vt.tiktok.com' in url:
                # Follow redirects to get the full URL
                response = self.session.head(url, allow_redirects=True, timeout=10)
                resolved_url = response.url
                print(f"Resolved TikTok URL: {url} -> {resolved_url}")
                return resolved_url
            return url
        except Exception as e:
            print(f"Failed to resolve TikTok URL {url}: {str(e)}")
            return url

    def extract_tiktok_fallback(self, url):
        """Fallback method for TikTok extraction using direct API calls"""
        try:
            print(f"Trying TikTok fallback extraction for: {url}")
            
            # Resolve short URL first
            resolved_url = self.resolve_tiktok_url(url)
            
            # Extract video ID from URL
            video_id_match = re.search(r'/video/(\d+)', resolved_url)
            if not video_id_match:
                raise Exception("Could not extract TikTok video ID")
            
            video_id = video_id_match.group(1)
            print(f"Extracted TikTok video ID: {video_id}")
            
            # Try multiple TikTok API endpoints
            api_urls = [
                f"https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/feed/?aweme_id={video_id}",
                f"https://api22-normal-c-useast1a.tiktokv.com/aweme/v1/aweme/detail/?aweme_id={video_id}",
                f"https://www.tiktok.com/api/item/detail/?itemId={video_id}"
            ]
            
            headers = {
                'User-Agent': 'com.ss.android.ugc.trill/494+PlayStore+%28Android+10%3B+SM-G975F%29',
                'Accept': 'application/json'
            }
            
            for api_url in api_urls:
                try:
                    response = self.session.get(api_url, headers=headers, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Extract video information
                        if 'aweme_list' in data and data['aweme_list']:
                            aweme = data['aweme_list'][0]
                        elif 'aweme_detail' in data:
                            aweme = data['aweme_detail']
                        elif 'itemInfo' in data and 'itemStruct' in data['itemInfo']:
                            aweme = data['itemInfo']['itemStruct']
                        else:
                            continue
                        
                        # Extract video URL and metadata
                        video_info = self.parse_tiktok_data(aweme)
                        if video_info:
                            return video_info
                            
                except Exception as e:
                    print(f"TikTok API {api_url} failed: {str(e)}")
                    continue
            
            raise Exception("All TikTok fallback methods failed")
            
        except Exception as e:
            print(f"TikTok fallback extraction failed: {str(e)}")
            raise e

    def parse_tiktok_data(self, aweme):
        """Parse TikTok API response data"""
        try:
            # Extract basic info
            desc = aweme.get('desc', 'TikTok Video')
            video_id = aweme.get('aweme_id', 'unknown')
            
            # Get author info
            author = aweme.get('author', {})
            username = author.get('unique_id', 'unknown')
            
            # Get video URLs
            video = aweme.get('video', {})
            play_addr = video.get('play_addr', {})
            
            # Try different URL sources
            video_url = None
            url_list = play_addr.get('url_list', [])
            
            if url_list:
                # Use the first available URL
                video_url = url_list[0]
            
            if not video_url:
                # Try alternative sources
                download_addr = video.get('download_addr', {})
                if download_addr.get('url_list'):
                    video_url = download_addr['url_list'][0]
            
            if not video_url:
                raise Exception("No video URL found in TikTok data")
            
            # Get additional metadata
            duration = video.get('duration', 0) / 1000 if video.get('duration') else 0
            
            # Statistics
            statistics = aweme.get('statistics', {})
            play_count = statistics.get('play_count', 0)
            
            # Create filename
            safe_desc = re.sub(r'[^\w\s-]', '', desc[:50])
            safe_desc = re.sub(r'[-\s]+', '-', safe_desc).strip('-')
            filename = f"TikTok_{username}_{safe_desc}_{video_id}.mp4"
            
            return {
                'direct_url': video_url,
                'title': desc,
                'filename': filename,
                'duration': duration,
                'platform': 'tiktok',
                'uploader': username,
                'view_count': play_count,
                'filesize': None,  # TikTok doesn't provide file size
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://www.tiktok.com/'
                }
            }
            
        except Exception as e:
            print(f"Failed to parse TikTok data: {str(e)}")
            raise e

    def extract_direct_url(self, url):
        """Main extraction method with platform-specific handling"""
        try:
            platform = self.detect_platform(url)
            print(f"Detected platform: {platform} for URL: {url}")
            
            # Handle TikTok with fallback methods
            if platform == 'tiktok':
                try:
                    # First try yt-dlp with TikTok-specific options
                    print("Trying yt-dlp for TikTok...")
                    return self.extract_with_ytdlp(url, self.tiktok_options)
                except Exception as e:
                    print(f"yt-dlp failed for TikTok: {str(e)}")
                    print("Trying TikTok fallback method...")
                    return self.extract_tiktok_fallback(url)
            
            # Handle other platforms with yt-dlp
            else:
                return self.extract_with_ytdlp(url, self.base_options)
                
        except Exception as e:
            logger.error(f"Failed to extract video from {url}: {str(e)}")
            raise e

    def extract_with_ytdlp(self, url, options):
        """Extract video using yt-dlp"""
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                print(f"Extracting info for: {url}")
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    raise Exception("No video information extracted")
                
                # Get the best video URL
                direct_url = None
                headers = {}
                
                if 'url' in info:
                    direct_url = info['url']
                elif 'formats' in info and info['formats']:
                    # Find the best format
                    best_format = None
                    for fmt in info['formats']:
                        if (fmt.get('url') and 
                            fmt.get('vcodec', 'none') != 'none'):
                            
                            if not best_format:
                                best_format = fmt
                            elif (fmt.get('height', 0) > best_format.get('height', 0)):
                                best_format = fmt
                    
                    if best_format:
                        direct_url = best_format['url']
                        headers = best_format.get('http_headers', {})
                
                if not direct_url:
                    raise Exception("Could not extract direct video URL")
                
                # Clean and prepare metadata
                title = info.get('title', 'Video')
                ext = info.get('ext', 'mp4')
                
                # Create safe filename
                safe_title = re.sub(r'[^\w\s-]', '', title[:100])
                safe_title = re.sub(r'[-\s]+', '-', safe_title).strip('-')
                filename = f"{safe_title}.{ext}"
                
                platform = self.detect_platform(url)
                
                return {
                    'direct_url': direct_url,
                    'title': title,
                    'filename': filename,
                    'filesize': info.get('filesize') or info.get('filesize_approx'),
                    'duration': info.get('duration'),
                    'platform': platform,
                    'headers': headers,
                    'thumbnail': info.get('thumbnail'),
                    'uploader': info.get('uploader'),
                    'view_count': info.get('view_count')
                }
                
        except Exception as e:
            print(f"yt-dlp extraction failed: {str(e)}")
            raise e

# Initialize extractor
extractor = RobustVideoExtractor()

@app.route('/api/download/quick', methods=['POST'])
def quick_download():
    """Quick download with robust TikTok handling"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        print(f"Processing URL: {url}")
        
        # Extract video information with fallbacks
        try:
            video_info = extractor.extract_direct_url(url)
            print(f"Successfully extracted video info: {video_info['title']}")
        except Exception as e:
            error_msg = str(e)
            print(f"Extraction failed: {error_msg}")
            
            # Provide user-friendly error messages
            if 'tiktok' in url.lower():
                if 'Unable to extract' in error_msg:
                    error_msg = "TikTok video extraction failed. This might be due to: 1) Video is private/deleted, 2) Geographic restrictions, or 3) TikTok has updated their system. Please try again or use a different video."
                elif 'HTTP Error 403' in error_msg or 'Forbidden' in error_msg:
                    error_msg = "TikTok blocked the request. Please wait a few minutes and try again, or try a different TikTok video."
            
            return jsonify({'error': error_msg}), 400
        
        download_id = str(uuid.uuid4())
        
        # Add to active downloads
        active_downloads[download_id] = {
            'id': download_id,
            'url': url,
            'status': 'ready',
            'platform': video_info['platform'],
            'title': video_info['title'],
            'filename': video_info['filename'],
            'filesize': video_info['filesize'],
            'created_at': datetime.now().isoformat(),
            'type': 'streaming'
        }
        
        return jsonify({
            'download_id': download_id,
            'stream_url': f'/api/stream/{download_id}',
            'filename': video_info['filename'],
            'filesize': video_info['filesize'],
            'title': video_info['title'],
            'platform': video_info['platform'],
            'duration': video_info['duration'],
            'thumbnail': video_info.get('thumbnail'),
            'uploader': video_info.get('uploader')
        })
        
    except Exception as e:
        logger.error(f"Error setting up quick download: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/stream/<download_id>')
def stream_video(download_id):
    """Stream video with robust error handling"""
    try:
        if download_id not in active_downloads:
            return jsonify({'error': 'Download not found'}), 404
        
        download_info = active_downloads[download_id]
        url = download_info['url']
        
        # Get fresh video info (URLs expire quickly)
        try:
            video_info = extractor.extract_direct_url(url)
        except Exception as e:
            return jsonify({'error': f'Could not refresh video URL: {str(e)}'}), 400
        
        direct_url = video_info['direct_url']
        filename = video_info['filename']
        
        def generate_stream():
            """Stream video data with progress tracking"""
            try:
                # Update status to streaming
                active_downloads[download_id]['status'] = 'streaming'
                socketio.emit('download_status', {
                    'id': download_id,
                    'status': 'streaming'
                })
                
                # Prepare headers (include platform-specific headers)
                stream_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': '*/*',
                    'Accept-Encoding': 'identity',
                    'Connection': 'keep-alive'
                }
                
                # Add platform-specific headers
                if video_info.get('headers'):
                    stream_headers.update(video_info['headers'])
                
                # Start streaming with retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        print(f"Streaming attempt {attempt + 1} for {download_id}")
                        
                        with requests.get(direct_url, headers=stream_headers, stream=True, timeout=30) as r:
                            r.raise_for_status()
                            
                            total_size = int(r.headers.get('content-length', 0))
                            downloaded = 0
                            chunk_size = 32768  # 32KB chunks
                            
                            # Update with total size
                            active_downloads[download_id]['total_bytes'] = total_size
                            
                            start_time = time.time()
                            last_progress_time = start_time
                            
                            # Stream chunks
                            for chunk in r.iter_content(chunk_size=chunk_size):
                                if chunk:
                                    downloaded += len(chunk)
                                    current_time = time.time()
                                    
                                    # Update progress every 0.5 seconds
                                    if current_time - last_progress_time >= 0.5:
                                        speed = downloaded / (current_time - start_time) if (current_time - start_time) > 0 else 0
                                        percentage = (downloaded / total_size * 100) if total_size > 0 else 0
                                        eta = (total_size - downloaded) / speed if speed > 0 and total_size > 0 else 0
                                        
                                        progress_data = {
                                            'id': download_id,
                                            'status': 'streaming',
                                            'downloaded_bytes': downloaded,
                                            'total_bytes': total_size,
                                            'speed': speed,
                                            'percentage': round(percentage, 1),
                                            'eta': eta
                                        }
                                        
                                        active_downloads[download_id].update(progress_data)
                                        socketio.emit('download_progress', progress_data)
                                        last_progress_time = current_time
                                    
                                    yield chunk
                        
                        # If we get here, streaming was successful
                        break
                        
                    except Exception as e:
                        print(f"Streaming attempt {attempt + 1} failed: {str(e)}")
                        if attempt == max_retries - 1:
                            raise e
                        time.sleep(2)  # Wait before retry
                
                # Mark as completed
                total_time = time.time() - start_time
                active_downloads[download_id]['status'] = 'completed'
                active_downloads[download_id]['total_time'] = total_time
                
                socketio.emit('download_status', {
                    'id': download_id,
                    'status': 'completed',
                    'percentage': 100,
                    'total_time': total_time
                })
                
            except Exception as e:
                logger.error(f"Streaming error for {download_id}: {str(e)}")
                if download_id in active_downloads:
                    active_downloads[download_id]['status'] = 'error'
                    active_downloads[download_id]['error'] = str(e)
                
                socketio.emit('download_status', {
                    'id': download_id,
                    'status': 'error',
                    'error': str(e)
                })
                raise
        
        # Create streaming response
        response = Response(
            stream_with_context(generate_stream()),
            mimetype='video/mp4',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Expose-Headers': 'Content-Disposition, Content-Length'
            }
        )
        
        # Add content length if available
        if video_info.get('filesize'):
            response.headers['Content-Length'] = str(video_info['filesize'])
        
        return response
        
    except Exception as e:
        logger.error(f"Error streaming video {download_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Keep your other endpoints (video-info, downloads, etc.)
@app.route('/api/video-info', methods=['POST'])
def get_video_info():
    """Get video information with robust TikTok handling"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        video_info = extractor.extract_direct_url(url)
        
        return jsonify({
            'title': video_info['title'],
            'filename': video_info['filename'],
            'filesize': video_info['filesize'],
            'duration': video_info['duration'],
            'platform': video_info['platform'],
            'thumbnail': video_info.get('thumbnail'),
            'uploader': video_info.get('uploader'),
            'view_count': video_info.get('view_count'),
            'streaming_available': True
        })
            
    except Exception as e:
        logger.error(f"Error getting video info: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check with TikTok status"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_downloads': len(active_downloads),
        'streaming_enabled': True,
        'tiktok_fallback_enabled': True,
        'version': 'robust'
    })

# WebSocket handlers
@socketio.on('connect')
def handle_connect():
    emit('connected', {
        'message': 'Connected to robust video downloader',
        'active_downloads': len(active_downloads)
    })

@socketio.on('disconnect')
def handle_disconnect():
    pass

def main():
    """Main function"""
    print("🚀 Robust Video Downloader Starting...")
    print("🎵 Enhanced TikTok support with fallback methods")
    
    port = int(os.environ.get('PORT', 4000))
    host = '0.0.0.0'
    
    print(f"🌐 Server available at: http://{host}:{port}")
    
    try:
        socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")

if __name__ == '__main__':
    main()