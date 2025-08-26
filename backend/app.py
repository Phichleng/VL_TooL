#!/usr/bin/env python3
"""
Flask Backend for Multi-Platform Video Downloader
Enhanced with improved real-time progress tracking
"""

import os
import sys
import json
import time
import uuid
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging

# Import your video downloader
try:
    from video_downloader import VideoDownloader, quick_download, batch_download, extract_video_links
except ImportError:
    print("Error: video_downloader.py not found. Please ensure it's in the same directory.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app, origins=["*"])
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Global variables
active_downloads = {}
download_queue = []
global_downloader = None

class EnhancedProgressTracker:
    """Enhanced progress tracker with better error handling and status updates"""
    
    def __init__(self, download_id, socketio_instance):
        self.download_id = download_id
        self.socketio = socketio_instance
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.last_percentage = 0
        self.total_bytes = 0
        self.downloaded_bytes = 0
        
    def progress_hook(self, d):
        """Enhanced progress hook for yt-dlp with better status tracking"""
        try:
            status = d.get('status', 'unknown')
            current_time = time.time()
            
            # Debug logging
            print(f"[{self.download_id[:8]}] Progress: {status}")
            
            if status == 'downloading':
                # Extract download information
                self.downloaded_bytes = d.get('downloaded_bytes', 0)
                self.total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                speed = d.get('speed', 0)
                eta = d.get('eta', 0)
                
                # Calculate percentage
                if self.total_bytes > 0:
                    percentage = (self.downloaded_bytes / self.total_bytes) * 100
                else:
                    percentage = 0
                
                # Get filename from path
                filename = ''
                if d.get('filename'):
                    filename = Path(d['filename']).name
                
                # Throttle updates (every 0.5 seconds or significant percentage change)
                percentage_change = abs(percentage - self.last_percentage)
                time_since_update = current_time - self.last_update_time
                
                if time_since_update >= 0.5 or percentage_change >= 1:
                    progress_data = {
                        'id': self.download_id,
                        'status': 'downloading',
                        'downloaded_bytes': self.downloaded_bytes,
                        'total_bytes': self.total_bytes,
                        'speed': speed,
                        'eta': eta,
                        'percentage': round(percentage, 1),
                        'filename': filename
                    }
                    
                    # Update global state
                    if self.download_id in active_downloads:
                        active_downloads[self.download_id].update(progress_data)
                    
                    # Emit progress update
                    self.socketio.emit('download_progress', progress_data)
                    
                    self.last_percentage = percentage
                    self.last_update_time = current_time
                    
                    print(f"[{self.download_id[:8]}] {percentage:.1f}% - {self._format_bytes(speed)}/s")
                    
            elif status == 'finished':
                # Download completed
                filename = ''
                if d.get('filename'):
                    filename = Path(d['filename']).name
                
                total_time = time.time() - self.start_time
                
                completion_data = {
                    'id': self.download_id,
                    'status': 'completed',
                    'filename': filename,
                    'percentage': 100,
                    'progress': 100,
                    'total_time': total_time,
                    'downloaded_bytes': self.total_bytes or self.downloaded_bytes,
                    'total_bytes': self.total_bytes or self.downloaded_bytes
                }
                
                # Update global state
                if self.download_id in active_downloads:
                    active_downloads[self.download_id].update(completion_data)
                
                # Emit completion status
                self.socketio.emit('download_status', completion_data)
                print(f"[{self.download_id[:8]}] ✅ Completed: {filename} ({self._format_time(total_time)})")
                
            elif status == 'error':
                error_msg = d.get('error', 'Download failed')
                
                error_data = {
                    'id': self.download_id,
                    'status': 'error',
                    'error': error_msg,
                    'percentage': 0
                }
                
                # Update global state
                if self.download_id in active_downloads:
                    active_downloads[self.download_id].update(error_data)
                
                self.socketio.emit('download_status', error_data)
                print(f"[{self.download_id[:8]}] ❌ Error: {error_msg}")
                
        except Exception as e:
            logger.error(f"Progress hook error for {self.download_id}: {str(e)}")
            # Send error status on hook failure
            self.socketio.emit('download_status', {
                'id': self.download_id,
                'status': 'error',
                'error': f'Progress tracking failed: {str(e)}'
            })
    
    def _format_bytes(self, bytes_val):
        """Format bytes for display"""
        if not bytes_val or bytes_val == 0:
            return '0 B'
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f} TB"
    
    def _format_time(self, seconds):
        """Format time for display"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs:02d}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins:02d}m"

def initialize_downloader():
    """Initialize the global downloader instance"""
    global global_downloader
    
    downloads_path = "./downloads"
    os.makedirs(downloads_path, exist_ok=True)
    
    global_downloader = VideoDownloader(
        download_path=downloads_path,
        remove_watermarks=False
    )
    
    return global_downloader

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_downloads': len(active_downloads)
    })

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    """Get or update downloader settings"""
    global global_downloader
    
    if request.method == 'GET':
        return jsonify({
            'download_path': str(global_downloader.download_path),
            'remove_watermarks': global_downloader.remove_watermarks,
            'ffmpeg_available': global_downloader.check_ffmpeg()
        })
    
    elif request.method == 'POST':
        data = request.json
        
        if 'download_path' in data:
            new_path = data['download_path']
            os.makedirs(new_path, exist_ok=True)
            global_downloader.download_path = Path(new_path)
        
        if 'remove_watermarks' in data:
            global_downloader.remove_watermarks = data['remove_watermarks']
        
        return jsonify({'message': 'Settings updated successfully'})

@app.route('/api/download/single', methods=['POST'])
def download_single_video():
    """Download a single video with enhanced progress tracking"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        custom_filename = data.get('custom_filename', '').strip() or None
        remove_watermark = data.get('remove_watermark', False)
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Generate unique download ID
        download_id = str(uuid.uuid4())
        
        # Add to active downloads with initial status
        active_downloads[download_id] = {
            'id': download_id,
            'url': url,
            'status': 'queued',
            'platform': global_downloader.detect_platform(url),
            'created_at': datetime.now().isoformat(),
            'custom_filename': custom_filename,
            'remove_watermark': remove_watermark,
            'progress': 0,
            'downloaded_bytes': 0,
            'total_bytes': 0,
            'speed': 0,
            'eta': 0,
            'filename': ''
        }
        
        print(f"🚀 Starting download: {download_id[:8]} - {url}")
        
        # Immediately emit the queued status
        socketio.emit('download_status', {
            'id': download_id,
            'status': 'queued',
            'url': url,
            'platform': global_downloader.detect_platform(url)
        })
        
        def download_worker():
            try:
                # Update to starting status
                active_downloads[download_id]['status'] = 'starting'
                socketio.emit('download_status', {
                    'id': download_id,
                    'status': 'starting'
                })
                
                print(f"📥 Download worker started for {download_id[:8]}")
                
                # Create enhanced progress tracker
                progress_tracker = EnhancedProgressTracker(download_id, socketio)
                
                # Create custom downloader instance
                custom_downloader = VideoDownloader(
                    download_path=global_downloader.download_path,
                    remove_watermarks=remove_watermark
                )
                
                # Add progress hook
                custom_downloader.base_options['progress_hooks'] = [progress_tracker.progress_hook]
                
                # Download the video
                success = custom_downloader.download_video(
                    url=url,
                    custom_filename=custom_filename,
                    remove_watermark=remove_watermark
                )
                
                print(f"📋 Download result for {download_id[:8]}: {success}")
                
                # Handle case where progress hook didn't catch completion
                if success and download_id in active_downloads:
                    current_status = active_downloads[download_id]['status']
                    if current_status not in ['completed', 'error']:
                        active_downloads[download_id]['status'] = 'completed'
                        active_downloads[download_id]['progress'] = 100
                        active_downloads[download_id]['percentage'] = 100
                        socketio.emit('download_status', {
                            'id': download_id,
                            'status': 'completed',
                            'progress': 100,
                            'percentage': 100
                        })
                        
                elif not success and download_id in active_downloads:
                    current_status = active_downloads[download_id]['status']
                    if current_status not in ['completed', 'error']:
                        active_downloads[download_id]['status'] = 'error'
                        active_downloads[download_id]['error'] = 'Download failed - no additional details'
                        socketio.emit('download_status', {
                            'id': download_id,
                            'status': 'error',
                            'error': 'Download failed - no additional details'
                        })
                            
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Download worker error for {download_id}: {error_msg}")
                print(f"💥 Download worker error for {download_id[:8]}: {error_msg}")
                
                if download_id in active_downloads:
                    active_downloads[download_id]['status'] = 'error'
                    active_downloads[download_id]['error'] = error_msg
                
                socketio.emit('download_status', {
                    'id': download_id,
                    'status': 'error',
                    'error': error_msg
                })
        
        # Start download in background thread
        thread = threading.Thread(target=download_worker, name=f"Download-{download_id[:8]}")
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'message': 'Download started',
            'download_id': download_id,
            'status': 'queued'
        })
        
    except Exception as e:
        logger.error(f"Error starting download: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/batch', methods=['POST'])
def download_batch_videos():
    """Download multiple videos with progress tracking"""
    try:
        data = request.json
        urls = data.get('urls', [])
        remove_watermark = data.get('remove_watermark', False)
        
        if not urls or not isinstance(urls, list):
            return jsonify({'error': 'URLs array is required'}), 400
        
        urls = [url.strip() for url in urls if url.strip()]
        
        if not urls:
            return jsonify({'error': 'No valid URLs provided'}), 400
        
        batch_id = str(uuid.uuid4())
        download_ids = []
        
        print(f"📦 Starting batch download: {batch_id[:8]} ({len(urls)} videos)")
        
        def batch_download_worker():
            try:
                for i, url in enumerate(urls):
                    download_id = str(uuid.uuid4())
                    download_ids.append(download_id)
                    
                    # Add to active downloads
                    active_downloads[download_id] = {
                        'id': download_id,
                        'url': url,
                        'status': 'queued',
                        'platform': global_downloader.detect_platform(url),
                        'created_at': datetime.now().isoformat(),
                        'batch_id': batch_id,
                        'batch_index': i + 1,
                        'batch_total': len(urls),
                        'remove_watermark': remove_watermark,
                        'progress': 0,
                        'downloaded_bytes': 0,
                        'total_bytes': 0,
                        'speed': 0,
                        'eta': 0,
                        'filename': ''
                    }
                    
                    # Emit batch progress
                    socketio.emit('batch_progress', {
                        'batch_id': batch_id,
                        'current': i + 1,
                        'total': len(urls),
                        'url': url
                    })
                    
                    try:
                        # Update to starting status
                        active_downloads[download_id]['status'] = 'starting'
                        socketio.emit('download_status', {
                            'id': download_id,
                            'status': 'starting'
                        })
                        
                        # Create progress tracker
                        progress_tracker = EnhancedProgressTracker(download_id, socketio)
                        
                        # Create custom downloader
                        custom_downloader = VideoDownloader(
                            download_path=global_downloader.download_path,
                            remove_watermarks=remove_watermark
                        )
                        custom_downloader.base_options['progress_hooks'] = [progress_tracker.progress_hook]
                        
                        success = custom_downloader.download_video(
                            url=url,
                            remove_watermark=remove_watermark
                        )
                        
                        if success:
                            if active_downloads[download_id]['status'] != 'completed':
                                active_downloads[download_id]['status'] = 'completed'
                                active_downloads[download_id]['progress'] = 100
                                socketio.emit('download_status', {
                                    'id': download_id,
                                    'status': 'completed',
                                    'progress': 100
                                })
                        else:
                            active_downloads[download_id]['status'] = 'error'
                            active_downloads[download_id]['error'] = 'Download failed'
                            socketio.emit('download_status', {
                                'id': download_id,
                                'status': 'error',
                                'error': 'Download failed'
                            })
                            
                    except Exception as e:
                        error_msg = str(e)
                        active_downloads[download_id]['status'] = 'error'
                        active_downloads[download_id]['error'] = error_msg
                        socketio.emit('download_status', {
                            'id': download_id,
                            'status': 'error',
                            'error': error_msg
                        })
                    
                    # Delay between downloads
                    time.sleep(2)
                
                # Emit batch completion
                socketio.emit('batch_complete', {
                    'batch_id': batch_id,
                    'download_ids': download_ids
                })
                
                print(f"✅ Batch download completed: {batch_id[:8]}")
                
            except Exception as e:
                logger.error(f"Batch download error: {str(e)}")
                socketio.emit('batch_error', {
                    'batch_id': batch_id,
                    'error': str(e)
                })
        
        # Start batch download
        thread = threading.Thread(target=batch_download_worker, name=f"Batch-{batch_id[:8]}")
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'message': 'Batch download started',
            'batch_id': batch_id,
            'total_urls': len(urls)
        })
        
    except Exception as e:
        logger.error(f"Error starting batch download: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/profile', methods=['POST'])
def download_profile_videos():
    """Download videos from a profile with progress tracking"""
    try:
        data = request.json
        profile_url = data.get('profile_url', '').strip()
        max_videos = data.get('max_videos')
        remove_watermark = data.get('remove_watermark', False)
        
        if not profile_url:
            return jsonify({'error': 'Profile URL is required'}), 400
        
        if max_videos:
            try:
                max_videos = int(max_videos)
            except ValueError:
                max_videos = None
        
        download_id = str(uuid.uuid4())
        
        active_downloads[download_id] = {
            'id': download_id,
            'url': profile_url,
            'status': 'queued',
            'platform': global_downloader.detect_platform(profile_url),
            'created_at': datetime.now().isoformat(),
            'type': 'profile',
            'max_videos': max_videos,
            'remove_watermark': remove_watermark,
            'progress': 0,
            'downloaded_bytes': 0,
            'total_bytes': 0,
            'speed': 0,
            'eta': 0,
            'filename': ''
        }
        
        print(f"👤 Starting profile download: {download_id[:8]} - {profile_url}")
        
        def profile_download_worker():
            try:
                # Update status
                active_downloads[download_id]['status'] = 'extracting_profile'
                socketio.emit('download_status', {
                    'id': download_id,
                    'status': 'extracting_profile'
                })
                
                # Create progress tracker
                progress_tracker = EnhancedProgressTracker(download_id, socketio)
                
                # Create custom downloader
                custom_downloader = VideoDownloader(
                    download_path=global_downloader.download_path,
                    remove_watermarks=remove_watermark
                )
                custom_downloader.base_options['progress_hooks'] = [progress_tracker.progress_hook]
                
                success = custom_downloader.download_profile_videos(
                    profile_url=profile_url,
                    max_videos=max_videos
                )
                
                if success:
                    if active_downloads[download_id]['status'] != 'completed':
                        active_downloads[download_id]['status'] = 'completed'
                        active_downloads[download_id]['progress'] = 100
                        socketio.emit('download_status', {
                            'id': download_id,
                            'status': 'completed',
                            'progress': 100
                        })
                else:
                    active_downloads[download_id]['status'] = 'error'
                    active_downloads[download_id]['error'] = 'Profile download failed'
                    socketio.emit('download_status', {
                        'id': download_id,
                        'status': 'error',
                        'error': 'Profile download failed'
                    })
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Profile download error: {error_msg}")
                active_downloads[download_id]['status'] = 'error'
                active_downloads[download_id]['error'] = error_msg
                socketio.emit('download_status', {
                    'id': download_id,
                    'status': 'error',
                    'error': error_msg
                })
        
        thread = threading.Thread(target=profile_download_worker, name=f"Profile-{download_id[:8]}")
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'message': 'Profile download started',
            'download_id': download_id
        })
        
    except Exception as e:
        logger.error(f"Error starting profile download: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/webpage', methods=['POST'])
def download_webpage_videos():
    """Extract and download videos from webpage with progress tracking"""
    try:
        data = request.json
        webpage_url = data.get('webpage_url', '').strip()
        max_videos = data.get('max_videos', 10)
        remove_watermark = data.get('remove_watermark', False)
        
        if not webpage_url:
            return jsonify({'error': 'Webpage URL is required'}), 400
        
        try:
            max_videos = int(max_videos)
        except ValueError:
            max_videos = 10
        
        download_id = str(uuid.uuid4())
        
        active_downloads[download_id] = {
            'id': download_id,
            'url': webpage_url,
            'status': 'queued',
            'platform': 'webpage',
            'created_at': datetime.now().isoformat(),
            'type': 'webpage',
            'max_videos': max_videos,
            'remove_watermark': remove_watermark,
            'progress': 0,
            'downloaded_bytes': 0,
            'total_bytes': 0,
            'speed': 0,
            'eta': 0,
            'filename': ''
        }
        
        print(f"🌐 Starting webpage extraction: {download_id[:8]} - {webpage_url}")
        
        def webpage_download_worker():
            try:
                # Update status
                active_downloads[download_id]['status'] = 'extracting_links'
                socketio.emit('download_status', {
                    'id': download_id,
                    'status': 'extracting_links'
                })
                
                # Create progress tracker
                progress_tracker = EnhancedProgressTracker(download_id, socketio)
                
                # Create custom downloader
                custom_downloader = VideoDownloader(
                    download_path=global_downloader.download_path,
                    remove_watermarks=remove_watermark
                )
                custom_downloader.base_options['progress_hooks'] = [progress_tracker.progress_hook]
                
                success = custom_downloader.download_from_webpage(
                    url=webpage_url,
                    max_videos=max_videos
                )
                
                if success:
                    if active_downloads[download_id]['status'] != 'completed':
                        active_downloads[download_id]['status'] = 'completed'
                        active_downloads[download_id]['progress'] = 100
                        socketio.emit('download_status', {
                            'id': download_id,
                            'status': 'completed',
                            'progress': 100
                        })
                else:
                    active_downloads[download_id]['status'] = 'error'
                    active_downloads[download_id]['error'] = 'Webpage extraction failed'
                    socketio.emit('download_status', {
                        'id': download_id,
                        'status': 'error',
                        'error': 'Webpage extraction failed'
                    })
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Webpage download error: {error_msg}")
                active_downloads[download_id]['status'] = 'error'
                active_downloads[download_id]['error'] = error_msg
                socketio.emit('download_status', {
                    'id': download_id,
                    'status': 'error',
                    'error': error_msg
                })
        
        thread = threading.Thread(target=webpage_download_worker, name=f"Webpage-{download_id[:8]}")
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'message': 'Webpage extraction started',
            'download_id': download_id
        })
        
    except Exception as e:
        logger.error(f"Error starting webpage download: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/video-info', methods=['POST'])
def get_video_info():
    """Get video information without downloading"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        info = global_downloader.get_video_info(url)
        
        if info:
            return jsonify(info)
        else:
            return jsonify({'error': 'Could not extract video information'}), 400
            
    except Exception as e:
        logger.error(f"Error getting video info: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

@app.route('/api/downloads/<download_id>', methods=['DELETE'])
def cancel_download(download_id):
    """Cancel a download"""
    try:
        if download_id in active_downloads:
            active_downloads[download_id]['status'] = 'cancelled'
            socketio.emit('download_status', {
                'id': download_id,
                'status': 'cancelled'
            })
            print(f"🚫 Download cancelled: {download_id[:8]}")
            return jsonify({'message': 'Download cancelled'})
        else:
            return jsonify({'error': 'Download not found'}), 404
    except Exception as e:
        logger.error(f"Error cancelling download: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/downloads/clear', methods=['POST'])
def clear_downloads():
    """Clear completed/failed downloads"""
    try:
        global active_downloads
        
        # Keep only active downloads
        before_count = len(active_downloads)
        active_downloads = {
            k: v for k, v in active_downloads.items() 
            if v['status'] in ['queued', 'starting', 'downloading', 'extracting', 'extracting_links', 'extracting_profile']
        }
        cleared_count = before_count - len(active_downloads)
        
        socketio.emit('downloads_cleared')
        print(f"🧹 Cleared {cleared_count} completed/failed downloads")
        
        return jsonify({
            'message': 'Downloads cleared',
            'cleared_count': cleared_count,
            'remaining': len(active_downloads)
        })
    except Exception as e:
        logger.error(f"Error clearing downloads: {str(e)}")
        return jsonify({'error': str(e)}), 500

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    print(f"🔌 Client connected: {request.sid}")
    emit('connected', {
        'message': 'Connected to video downloader',
        'active_downloads': len(active_downloads)
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    print(f"🔌 Client disconnected: {request.sid}")

@socketio.on('get_downloads')
def handle_get_downloads():
    """Send current downloads to client"""
    emit('downloads_update', {
        'downloads': list(active_downloads.values()),
        'total': len(active_downloads)
    })
    print(f"📤 Sent {len(active_downloads)} downloads to client")

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

def main():
    """Main function to run the Flask server"""
    # Initialize the downloader
    initialize_downloader()
    
    print("🚀 Enhanced Video Downloader Backend Starting...")
    print(f"📁 Download directory: {global_downloader.download_path}")
    print(f"🔧 FFmpeg available: {global_downloader.check_ffmpeg()}")
    print("🌐 Server will be available at: http://localhost:5000")
    print("📡 WebSocket endpoint: ws://localhost:5000")
    print("\n💡 API Endpoints:")
    print("   GET  /api/health          - Health check")
    print("   GET  /api/settings        - Get settings") 
    print("   POST /api/settings        - Update settings")
    print("   POST /api/download/single - Download single video")
    print("   POST /api/download/batch  - Download multiple videos")
    print("   POST /api/download/profile - Download profile videos")
    print("   POST /api/download/webpage - Extract from webpage")
    print("   POST /api/video-info      - Get video information")
    print("   GET  /api/downloads       - List active downloads")
    print("   POST /api/downloads/clear - Clear completed downloads")
    print("   DEL  /api/downloads/<id>  - Cancel download")
    
    # Run the server
    try:
        socketio.run(
            app,
            host='0.0.0.0',
            port=4000,
            debug=False,  # Set to False for better performance
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {str(e)}")

if __name__ == '__main__':
    main()