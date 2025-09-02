#!/usr/bin/env python3
"""
Enhanced Flask Backend with Direct Streaming Support
Eliminates the two-step download process
"""

import os
import sys
import json
import time
import uuid
import threading
import re
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import io
import logging
import requests
import yt_dlp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app, origins=["*"])
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Global variables
active_downloads = {}

class StreamingVideoExtractor:
    """Enhanced video extractor for direct streaming"""
    
    def __init__(self):
        self.base_options = {
            'quiet': True,
            'no_warnings': True,
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
            'retries': 3,
            'fragment_retries': 3,
            'socket_timeout': 30
        }
    
    def extract_direct_url(self, url):
        """Extract direct video URL and metadata with improved error handling"""
        try:
            platform = self.detect_platform(url)
            
            # Special handling for TikTok
            if platform == 'tiktok':
                return self._extract_tiktok_video(url)
            
            # For other platforms, use standard yt-dlp
            with yt_dlp.YoutubeDL(self.base_options) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Get the best video URL
                direct_url = None
                headers = {}
                
                if 'url' in info:
                    direct_url = info['url']
                elif 'formats' in info and info['formats']:
                    # Find the best format with video
                    best_format = None
                    for fmt in info['formats']:
                        if (fmt.get('url') and 
                            fmt.get('vcodec', 'none') != 'none' and
                            fmt.get('acodec', 'none') != 'none'):  # Video + Audio
                            
                            if not best_format:
                                best_format = fmt
                            elif (fmt.get('height', 0) > best_format.get('height', 0) or
                                  fmt.get('quality', 0) > best_format.get('quality', 0)):
                                best_format = fmt
                    
                    # If no combined format, try video-only
                    if not best_format:
                        for fmt in info['formats']:
                            if (fmt.get('url') and 
                                fmt.get('vcodec', 'none') != 'none'):
                                best_format = fmt
                                break
                    
                    if best_format:
                        direct_url = best_format['url']
                        headers = best_format.get('http_headers', {})
                
                if not direct_url:
                    raise Exception("Could not extract direct video URL")
                
                # Clean filename
                title = info.get('title', 'video')
                ext = info.get('ext', 'mp4')
                
                # Remove invalid characters for filename
                safe_title = re.sub(r'[^\w\s-]', '', title)
                safe_title = re.sub(r'[-\s]+', '-', safe_title)
                filename = f"{safe_title}.{ext}"
                
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
            logger.error(f"Error extracting video info: {str(e)}")
            raise e
    
    def _extract_tiktok_video(self, url):
        """Improved TikTok extraction method with better error handling"""
        try:
            # Try using yt-dlp first with enhanced options
            tiktok_options = self.base_options.copy()
            tiktok_options.update({
                'extractor_args': {
                    'tiktok': {
                        'webpage_url_basename': 'video',
                        'app_version': '29.3.0',
                        'manifest_app_version': '2913030'
                    }
                }
            })
            
            with yt_dlp.YoutubeDL(tiktok_options) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                    
                    if info and info.get('url'):
                        # Clean filename
                        title = info.get('title', 'tiktok_video') or 'tiktok_video'
                        ext = info.get('ext', 'mp4')
                        
                        safe_title = re.sub(r'[^\w\s-]', '', str(title))
                        safe_title = re.sub(r'[-\s]+', '-', safe_title)
                        filename = f"{safe_title}.{ext}"
                        
                        return {
                            'direct_url': info['url'],
                            'title': title,
                            'filename': filename,
                            'filesize': info.get('filesize') or info.get('filesize_approx'),
                            'duration': info.get('duration'),
                            'platform': 'tiktok',
                            'headers': {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                'Referer': 'https://www.tiktok.com/',
                                'Origin': 'https://www.tiktok.com',
                                'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
                                'Accept-Language': 'en-US,en;q=0.5',
                                'Range': 'bytes=0-',
                                'Sec-Fetch-Dest': 'video',
                                'Sec-Fetch-Mode': 'no-cors',
                                'Sec-Fetch-Site': 'same-site'
                            },
                            'thumbnail': info.get('thumbnail'),
                            'uploader': info.get('uploader'),
                            'view_count': info.get('view_count')
                        }
                    else:
                        logger.warning("yt-dlp succeeded but no URL found in info")
                        
                except Exception as ydl_error:
                    logger.warning(f"yt-dlp extraction failed: {str(ydl_error)}")
                    # Continue to fallback method
                    pass
            
            # Fallback method with improved error handling
            return self._tiktok_fallback_extraction(url)
            
        except Exception as e:
            logger.error(f"TikTok extraction failed completely: {str(e)}")
            raise Exception(f"Could not extract TikTok video: {str(e)}")
    
    def _tiktok_fallback_extraction(self, url):
        """Improved fallback method for TikTok video extraction"""
        try:
            # Extract video ID from URL
            video_id = self._extract_tiktok_id(url)
            if not video_id:
                # If we can't extract ID, try direct webpage parsing
                return self._tiktok_webpage_fallback(url)
            
            logger.info(f"Extracted TikTok video ID: {video_id}")
            
            # Try multiple API endpoints with updated domains
            api_endpoints = [
                f"https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/feed/?aweme_id={video_id}",
                f"https://api16-normal-c-useast2a.tiktokv.com/aweme/v1/feed/?aweme_id={video_id}",
                f"https://api.tiktokv.com/aweme/v1/feed/?aweme_id={video_id}",
                f"https://api19-normal-c-useast1a.tiktokv.com/aweme/v1/feed/?aweme_id={video_id}",
                f"https://www.tiktok.com/api/item/detail/?itemId={video_id}"
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.tiktok.com/',
                'Origin': 'https://www.tiktok.com',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'Authority': 'api16-normal-c-useast1a.tiktokv.com'
            }
            
            for api_url in api_endpoints:
                try:
                    response = requests.get(api_url, headers=headers, timeout=15)
                    if response.status_code == 200:
                        try:
                            data = response.json()
                        except json.JSONDecodeError:
                            logger.warning(f"API returned non-JSON response from {api_url}")
                            continue
                        
                        if data.get('aweme_list') and len(data['aweme_list']) > 0:
                            video_data = data['aweme_list'][0]
                            video_urls = video_data.get('video', {}).get('play_addr', {}).get('url_list', [])
                            
                            if video_urls:
                                # Get the highest quality URL
                                direct_url = video_urls[0]
                                # Remove watermark parameter if present
                                if 'playwm' in direct_url:
                                    direct_url = direct_url.replace('playwm', 'play')
                                
                                title = video_data.get('desc', f'tiktok_{video_id}') or f'tiktok_{video_id}'
                                
                                return {
                                    'direct_url': direct_url,
                                    'title': title,
                                    'filename': f"tiktok_{video_id}.mp4",
                                    'filesize': None,
                                    'duration': video_data.get('duration', 0) / 1000 if video_data.get('duration') else None,
                                    'platform': 'tiktok',
                                    'headers': {
                                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                        'Referer': 'https://www.tiktok.com/',
                                        'Origin': 'https://www.tiktok.com',
                                        'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
                                        'Accept-Language': 'en-US,en;q=0.5',
                                        'Range': 'bytes=0-',
                                        'Sec-Fetch-Dest': 'video',
                                        'Sec-Fetch-Mode': 'no-cors',
                                        'Sec-Fetch-Site': 'same-site'
                                    },
                                    'thumbnail': video_data.get('video', {}).get('cover', {}).get('url_list', [None])[0],
                                    'uploader': video_data.get('author', {}).get('unique_id', 'unknown'),
                                    'view_count': video_data.get('statistics', {}).get('play_count', 0)
                                }
                        except KeyError as e:
                            logger.warning(f"Key error in API response from {api_url}: {str(e)}")
                            continue
                except requests.RequestException as e:
                    logger.warning(f"API endpoint {api_url} failed: {str(e)}")
                    continue
            
            # If all API attempts fail, try webpage parsing
            return self._tiktok_webpage_fallback(url)
            
        except Exception as e:
            logger.error(f"TikTok fallback extraction failed: {str(e)}")
            raise Exception(f"All TikTok extraction methods failed: {str(e)}")
    
    def _extract_tiktok_id(self, url):
        """Extract TikTok video ID from URL with improved patterns"""
        patterns = [
            r'tiktok\.com/.+?/video/(\d+)',
            r'tiktok\.com/@[^/]+/video/(\d+)',
            r'vm\.tiktok\.com/([a-zA-Z0-9]+)',
            r'vt\.tiktok\.com/([a-zA-Z0-9]+)',
            r'tiktok\.com/t/([a-zA-Z0-9]+)',
            r'/video/(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        logger.warning(f"Could not extract TikTok ID from URL: {url}")
        return None
    
    def _tiktok_webpage_fallback(self, url):
        """Parse TikTok webpage directly as last resort"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1'
            }
            
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            html_content = response.text
            
            # Try to extract video URL from JSON data in HTML
            json_patterns = [
                r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>',
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                r'"downloadAddr":"([^"]+)"',
                r'"playAddr":"([^"]+)"',
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, html_content, re.DOTALL)
                if matches:
                    try:
                        # Try to parse as JSON first
                        if pattern.startswith('<script') or pattern.startswith('window'):
                            json_data = json.loads(matches[0])
                            # Navigate through JSON structure to find video URL
                            video_url = self._find_video_url_in_json(json_data)
                            if video_url:
                                if 'playwm' in video_url:
                                    video_url = video_url.replace('playwm', 'play')
                                
                                # Extract title from HTML
                                title_match = re.search(r'<title>([^<]+)</title>', html_content)
                                title = title_match.group(1) if title_match else 'tiktok_video'
                                title = title.replace(' | TikTok', '').strip()
                                
                                return {
                                    'direct_url': video_url,
                                    'title': title,
                                    'filename': f"tiktok_{int(time.time())}.mp4",
                                    'filesize': None,
                                    'duration': None,
                                    'platform': 'tiktok',
                                    'headers': headers,
                                    'thumbnail': None,
                                    'uploader': 'unknown',
                                    'view_count': 0
                                }
                        else:
                            # Direct URL match
                            video_url = matches[0]
                            if 'playwm' in video_url:
                                video_url = video_url.replace('playwm', 'play')
                            
                            title_match = re.search(r'<title>([^<]+)</title>', html_content)
                            title = title_match.group(1) if title_match else 'tiktok_video'
                            title = title.replace(' | TikTok', '').strip()
                            
                            return {
                                'direct_url': video_url,
                                'title': title,
                                'filename': f"tiktok_{int(time.time())}.mp4",
                                'filesize': None,
                                'duration': None,
                                'platform': 'tiktok',
                                'headers': headers,
                                'thumbnail': None,
                                'uploader': 'unknown',
                                'view_count': 0
                            }
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"JSON parsing failed for pattern {pattern}: {str(e)}")
                        continue
            
            # Try direct video URL patterns
            video_patterns = [
                r'https://[^"]*\.tiktokcdn\.com/[^"]*\.mp4[^"]*',
                r'https://v\d{2}\.tiktokcdn\.com/[^"]*',
                r'"url":"(https://[^"]*tiktokcdn[^"]*\.mp4[^"]*)"'
            ]
            
            for pattern in video_patterns:
                matches = re.findall(pattern, html_content)
                if matches:
                    video_url = matches[0]
                    # Clean up the URL
                    video_url = video_url.replace('\\u002F', '/').replace('\\', '')
                    if 'playwm' in video_url:
                        video_url = video_url.replace('playwm', 'play')
                    
                    # Extract title from HTML
                    title_match = re.search(r'<title>([^<]+)</title>', html_content)
                    title = title_match.group(1) if title_match else 'tiktok_video'
                    title = title.replace(' | TikTok', '').strip()
                    
                    return {
                        'direct_url': video_url,
                        'title': title,
                        'filename': f"tiktok_{int(time.time())}.mp4",
                        'filesize': None,
                        'duration': None,
                        'platform': 'tiktok',
                        'headers': headers,
                        'thumbnail': None,
                        'uploader': 'unknown',
                        'view_count': 0
                    }
            
            raise Exception("No video URL found in webpage")
            
        except Exception as e:
            logger.error(f"TikTok webpage fallback failed: {str(e)}")
            raise Exception(f"Webpage parsing failed: {str(e)}")
    
    def _find_video_url_in_json(self, data):
        """Recursively search for video URL in JSON data"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ['downloadAddr', 'playAddr', 'videoUrl', 'url'] and isinstance(value, str) and value.startswith('http'):
                    return value
                result = self._find_video_url_in_json(value)
                if result:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self._find_video_url_in_json(item)
                if result:
                    return result
        return None
    
    def detect_platform(self, url):
        """Detect video platform"""
        domain = url.lower()
        if 'tiktok.com' in domain or 'vm.tiktok.com' in domain or 'vt.tiktok.com' in domain:
            return 'tiktok'
        elif 'youtube.com' in domain or 'youtu.be' in domain:
            return 'youtube'
        elif 'instagram.com' in domain:
            return 'instagram'
        elif 'facebook.com' in domain or 'fb.watch' in domain:
            return 'facebook'
        elif 'douyin.com' in domain or 'v.douyin.com' in domain:
            return 'douyin'
        else:
            return 'unknown'

# Initialize extractor
extractor = StreamingVideoExtractor()

@app.route('/api/download/stream', methods=['POST'])
def stream_download():
    """Set up streaming download"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Extract video information
        try:
            video_info = extractor.extract_direct_url(url)
        except Exception as e:
            logger.error(f"Extraction error: {str(e)}")
            return jsonify({'error': f'Could not extract video: {str(e)}'}), 400
        
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
            'progress': 0,
            'downloaded_bytes': 0,
            'total_bytes': video_info['filesize'] or 0
        }
        
        # Emit status
        socketio.emit('download_status', {
            'id': download_id,
            'status': 'ready',
            'title': video_info['title'],
            'filename': video_info['filename']
        })
        
        return jsonify({
            'download_id': download_id,
            'stream_url': f'/api/stream/{download_id}',
            'filename': video_info['filename'],
            'filesize': video_info['filesize'],
            'title': video_info['title'],
            'platform': video_info['platform']
        })
        
    except Exception as e:
        logger.error(f"Error setting up stream: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stream/<download_id>')
def stream_video(download_id):
    """Stream video directly to client"""
    try:
        if download_id not in active_downloads:
            return jsonify({'error': 'Download not found'}), 404
        
        download_info = active_downloads[download_id]
        url = download_info['url']
        
        # Get fresh video info (URLs expire)
        try:
            video_info = extractor.extract_direct_url(url)
        except Exception as e:
            logger.error(f"Could not refresh video URL: {str(e)}")
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
                
                # Prepare headers
                stream_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': '*/*',
                    'Accept-Encoding': 'identity',
                    'Connection': 'keep-alive',
                    'Range': 'bytes=0-',  # Support range requests
                    'Referer': 'https://www.tiktok.com/' if video_info['platform'] == 'tiktok' else '',
                    'Origin': 'https://www.tiktok.com' if video_info['platform'] == 'tiktok' else ''
                }
                
                # Add platform-specific headers
                if video_info.get('headers'):
                    stream_headers.update(video_info['headers'])
                
                # Start streaming
                with requests.get(direct_url, headers=stream_headers, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    
                    total_size = int(r.headers.get('content-length', 0))
                    downloaded = 0
                    chunk_size = 32768  # 32KB chunks for better performance
                    
                    # Update with total size
                    active_downloads[download_id]['total_bytes'] = total_size
                    active_downloads[download_id]['status'] = 'streaming'
                    
                    start_time = time.time()
                    last_progress_time = start_time
                    
                    # Stream chunks with progress tracking
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:
                            downloaded += len(chunk)
                            current_time = time.time()
                            
                            # Update progress every 0.5 seconds
                            if current_time - last_progress_time >= 0.5:
                                speed = downloaded / (current_time - start_time) if (current_time - start_time) > 0 else 0
                                percentage = (downloaded / total_size * 100) if total_size > 0 else 0
                                eta = (total_size - downloaded) / speed if speed > 0 else 0
                                
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
        
        # Create streaming response with proper headers
        response = Response(
            stream_with_context(generate_stream()),
            mimetype='video/mp4',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
                'X-Content-Type-Options': 'nosniff',
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

@app.route('/api/download/quick', methods=['POST'])
def quick_download():
    """Quick download that returns direct stream URL immediately"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Extract video information
        try:
            video_info = extractor.extract_direct_url(url)
        except Exception as e:
            logger.error(f"Quick download extraction error: {str(e)}")
            return jsonify({'error': f'Could not extract video: {str(e)}'}), 400
        
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/video-info', methods=['POST'])
def get_video_info():
    """Get video information without downloading"""
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

# Keep your existing endpoints for compatibility
@app.route('/api/download/single', methods=['POST'])
def download_single_video():
    """Legacy endpoint - redirects to streaming"""
    return quick_download()

@app.route('/api/downloads', methods=['GET'])
def list_downloads():
    """Get list of all downloads"""
    try:
        return jsonify({
            'active_downloads': list(active_downloads.values()),
            'total_active': len(active_downloads)
        })
    except Exception as e:
        logger.error(f"Error listing downloads: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/downloads/clear', methods=['POST'])
def clear_downloads():
    """Clear completed/failed downloads"""
    try:
        global active_downloads
        
        before_count = len(active_downloads)
        active_downloads = {
            k: v for k, v in active_downloads.items() 
            if v['status'] in ['queued', 'starting', 'streaming', 'ready']
        }
        cleared_count = before_count - len(active_downloads)
        
        socketio.emit('downloads_cleared')
        
        return jsonify({
            'message': 'Downloads cleared',
            'cleared_count': cleared_count,
            'remaining': len(active_downloads)
        })
    except Exception as e:
        logger.error(f"Error clearing downloads: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_downloads': len(active_downloads),
        'streaming_enabled': True,
        'version': 'streaming'
    })

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    print(f"Client connected: {request.sid}")
    emit('connected', {
        'message': 'Connected to streaming video downloader',
        'active_downloads': len(active_downloads)
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    print(f"Client disconnected: {request.sid}")

@socketio.on('get_downloads')
def handle_get_downloads():
    """Send current downloads to client"""
    emit('downloads_update', {
        'downloads': list(active_downloads.values()),
        'total': len(active_downloads)
    })

@app.route('/', methods=['GET'])
def serve_frontend():
    """Serve the enhanced frontend"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>', methods=['GET'])
def serve_static(path):
    """Serve static files"""
    return send_from_directory('.', path)

def main():
    """Main function to run the Flask server"""
    print("🚀 Enhanced Streaming Video Downloader Starting...")
    print("⚡ Direct streaming enabled - no server storage needed!")
    
    # Get port from environment variable
    port = int(os.environ.get('PORT', 4000))
    host = '0.0.0.0'
    
    print(f"🌐 Server available at: http://{host}:{port}")
    print("💡 API Endpoints:")
    print("   POST /api/download/quick   - Quick streaming download")
    print("   POST /api/download/stream  - Set up streaming download") 
    print("   GET  /api/stream/<id>      - Stream video file")
    print("   POST /api/video-info       - Get video information")
    print("   GET  /api/downloads        - List downloads")
    print("   POST /api/downloads/clear  - Clear downloads")
    
    try:
        socketio.run(
            app,
            host=host,
            port=port,
            debug=False,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Server error: {str(e)}")

if __name__ == '__main__':
    main()