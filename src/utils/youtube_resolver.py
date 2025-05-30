#!/usr/bin/env python3
"""
YouTube URL resolver utility using yt-dlp
This module provides functionality to extract direct video stream URLs from YouTube links
for playback in VLC player.
"""

import subprocess
import json
import logging
from typing import Optional, Dict, Any

class YouTubeResolver:
    """Resolves YouTube URLs to direct stream URLs using yt-dlp"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def is_youtube_url(self, url: str) -> bool:
        """Check if the URL is a YouTube URL"""
        youtube_domains = [
            'youtube.com',
            'www.youtube.com',
            'youtu.be',
            'm.youtube.com'
        ]
        return any(domain in url.lower() for domain in youtube_domains)
    
    def extract_stream_url(self, youtube_url: str) -> Optional[str]:
        """Extract the direct stream URL from a YouTube URL using yt-dlp
        
        Args:
            youtube_url: The YouTube URL to resolve
            
        Returns:
            Direct stream URL if successful, None otherwise
        """
        try:
            # Use yt-dlp to extract video information
            cmd = [
                'yt-dlp',
                '--no-download',
                '--print', 'url',
                '--format', 'best[ext=mp4]/best',  # Prefer mp4 format
                youtube_url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            if result.returncode == 0 and result.stdout.strip():
                stream_url = result.stdout.strip()
                self.logger.info(f"Successfully extracted stream URL for: {youtube_url}")
                return stream_url
            else:
                self.logger.error(f"yt-dlp failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout while extracting URL: {youtube_url}")
            return None
        except FileNotFoundError:
            self.logger.error("yt-dlp not found. Please install yt-dlp: pip install yt-dlp")
            return None
        except Exception as e:
            self.logger.error(f"Error extracting stream URL: {e}")
            return None
    
    def get_video_info(self, youtube_url: str) -> Optional[Dict[str, Any]]:
        """Get detailed video information from YouTube URL
        
        Args:
            youtube_url: The YouTube URL to analyze
            
        Returns:
            Dictionary with video information if successful, None otherwise
        """
        try:
            cmd = [
                'yt-dlp',
                '--no-download',
                '--dump-json',
                youtube_url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                info = json.loads(result.stdout)
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'upload_date': info.get('upload_date', ''),
                    'description': info.get('description', ''),
                    'thumbnail': info.get('thumbnail', ''),
                    'formats': info.get('formats', [])
                }
            else:
                self.logger.error(f"Failed to get video info: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout while getting video info: {youtube_url}")
            return None
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Error getting video info: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return None
    
    def resolve_url(self, url: str) -> str:
        """Resolve URL - if it's YouTube, extract stream URL, otherwise return as-is
        
        Args:
            url: The URL to resolve
            
        Returns:
            Direct stream URL for YouTube links, original URL for others
        """
        if self.is_youtube_url(url):
            stream_url = self.extract_stream_url(url)
            if stream_url:
                return stream_url
            else:
                # Fallback to original URL if extraction fails
                self.logger.warning(f"Failed to extract stream URL, using original: {url}")
                return url
        else:
            return url

# Global instance for easy access
youtube_resolver = YouTubeResolver()