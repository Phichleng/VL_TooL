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
        """Extract direct video URL and metadata"""
        try:
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
                import re
                safe_title = re.sub(r'[^\w\s-]', '', title)
                safe_title = re.sub(r'[-\s]+', '-', safe_title)
                filename = f"{safe_title}.{ext}"
                
                return {
                    'direct_url': direct_url,
                    'title': title,
                    'filename': filename,
                    'filesize': info.get('filesize') or info.get('filesize_approx'),
                    'duration': info.get('duration'),
                    'platform': self.detect_platform(url),
                    'headers': headers,
                    'thumbnail': info.get('thumbnail'),
                    'uploader': info.get('uploader'),
                    'view_count': info.get('view_count')
                }
                
        except Exception as e:
            logger.error(f"Error extracting video info: {str(e)}")
            raise e
    
    def detect_platform(self, url):
        """Detect video platform"""
        domain = url.lower()
        if 'tiktok.com' in domain or 'vm.tiktok.com' in domain:
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
                    'Range': 'bytes=0-'  # Support range requests
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