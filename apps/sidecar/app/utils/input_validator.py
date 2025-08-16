"""
Comprehensive Input Validation and Sanitization System for Sclip
Provides validation and sanitization for all user inputs and API requests
"""
import re
import os
import hashlib
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pathlib import Path

from .logger import get_logger
from .error_handler import SclipError, ErrorCode, ErrorCategory, ErrorSeverity

logger = get_logger(__name__)

class InputValidator:
    """Comprehensive input validation and sanitization"""
    
    def __init__(self):
        # File type restrictions
        self.allowed_file_types = {
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'],
            'video': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'],
            'audio': ['.mp3', '.wav', '.aac', '.ogg', '.flac'],
            'document': ['.txt', '.pdf', '.doc', '.docx']
        }
        
        # File size limits (in bytes)
        self.file_size_limits = {
            'image': 10 * 1024 * 1024,  # 10MB
            'video': 500 * 1024 * 1024,  # 500MB
            'audio': 50 * 1024 * 1024,   # 50MB
            'document': 5 * 1024 * 1024  # 5MB
        }
        
        # Rate limiting
        self.rate_limits = {
            'api_requests': {'max_requests': 100, 'window_seconds': 3600},
            'file_uploads': {'max_uploads': 10, 'window_seconds': 3600},
            'session_creation': {'max_sessions': 5, 'window_seconds': 3600}
        }
    
    def validate_user_prompt(self, prompt: str) -> Dict[str, Any]:
        """Validate user prompt input"""
        errors = []
        
        # Check length
        if not prompt or len(prompt.strip()) == 0:
            errors.append("Prompt cannot be empty")
        elif len(prompt) > 1000:
            errors.append("Prompt too long (max 1000 characters)")
        
        # Check for malicious content
        if self._contains_malicious_content(prompt):
            errors.append("Prompt contains potentially malicious content")
        
        # Check for inappropriate content
        if self._contains_inappropriate_content(prompt):
            errors.append("Prompt contains inappropriate content")
        
        if errors:
            raise SclipError(
                message="Prompt validation failed",
                error_code=ErrorCode.INVALID_INPUT,
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW,
                details={"errors": errors, "prompt_length": len(prompt)}
            )
        
        return {
            "valid": True,
            "sanitized_prompt": self._sanitize_text(prompt),
            "word_count": len(prompt.split()),
            "estimated_duration": self._estimate_prompt_duration(prompt)
        }
    
    def validate_file_upload(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """Validate file upload"""
        errors = []
        
        # Check file exists
        if not os.path.exists(file_path):
            errors.append("File does not exist")
            raise SclipError(
                message="File validation failed",
                error_code=ErrorCode.FILE_NOT_FOUND,
                category=ErrorCategory.FILE_OPERATION,
                severity=ErrorSeverity.MEDIUM,
                details={"errors": errors, "file_path": file_path}
            )
        
        # Check file extension
        file_ext = Path(file_path).suffix.lower()
        if file_type not in self.allowed_file_types:
            errors.append(f"Invalid file type: {file_type}")
        elif file_ext not in self.allowed_file_types[file_type]:
            errors.append(f"File extension {file_ext} not allowed for {file_type}")
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > self.file_size_limits[file_type]:
            errors.append(f"File too large: {file_size} bytes (max {self.file_size_limits[file_type]})")
        
        # Check file content (basic)
        if not self._is_valid_file_content(file_path, file_type):
            errors.append("File content validation failed")
        
        if errors:
            raise SclipError(
                message="File validation failed",
                error_code=ErrorCode.INVALID_INPUT,
                category=ErrorCategory.FILE_OPERATION,
                severity=ErrorSeverity.MEDIUM,
                details={"errors": errors, "file_path": file_path, "file_size": file_size}
            )
        
        return {
            "valid": True,
            "file_path": file_path,
            "file_size": file_size,
            "file_hash": self._calculate_file_hash(file_path),
            "safe_filename": self._sanitize_filename(file_path)
        }
    
    def validate_api_request(self, request_data: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
        """Validate API request data"""
        errors = []
        
        # Check required fields based on endpoint
        required_fields = self._get_required_fields(endpoint)
        for field in required_fields:
            if field not in request_data:
                errors.append(f"Missing required field: {field}")
        
        # Validate field types and values
        for field, value in request_data.items():
            field_errors = self._validate_field(field, value, endpoint)
            errors.extend(field_errors)
        
        # Check for suspicious patterns
        if self._contains_suspicious_patterns(request_data):
            errors.append("Request contains suspicious patterns")
        
        if errors:
            raise SclipError(
                message="API request validation failed",
                error_code=ErrorCode.INVALID_INPUT,
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                details={"errors": errors, "endpoint": endpoint}
            )
        
        return {
            "valid": True,
            "sanitized_data": self._sanitize_request_data(request_data),
            "request_hash": self._calculate_request_hash(request_data)
        }
    
    def validate_session_data(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate session data"""
        errors = []
        
        # Check session ID format
        session_id = session_data.get('session_id')
        if not session_id or not self._is_valid_session_id(session_id):
            errors.append("Invalid session ID format")
        
        # Check user ID
        user_id = session_data.get('user_id')
        if user_id and not self._is_valid_user_id(user_id):
            errors.append("Invalid user ID format")
        
        # Check timestamp
        timestamp = session_data.get('timestamp')
        if timestamp and not self._is_valid_timestamp(timestamp):
            errors.append("Invalid timestamp format")
        
        if errors:
            raise SclipError(
                message="Session data validation failed",
                error_code=ErrorCode.INVALID_INPUT,
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                details={"errors": errors}
            )
        
        return {
            "valid": True,
            "sanitized_session": self._sanitize_session_data(session_data)
        }
    
    def _contains_malicious_content(self, text: str) -> bool:
        """Check for malicious content in text"""
        malicious_patterns = [
            r'<script.*?>.*?</script>',  # Script tags
            r'javascript:',              # JavaScript protocol
            r'data:text/html',          # Data URLs
            r'vbscript:',               # VBScript
            r'on\w+\s*=',               # Event handlers
            r'<iframe.*?>',             # Iframe tags
            r'<object.*?>',             # Object tags
            r'<embed.*?>',              # Embed tags
        ]
        
        for pattern in malicious_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _contains_inappropriate_content(self, text: str) -> bool:
        """Check for inappropriate content"""
        # This is a basic implementation - can be enhanced with more sophisticated content filtering
        inappropriate_words = [
            'spam', 'scam', 'hack', 'crack', 'warez', 'porn', 'adult'
        ]
        
        text_lower = text.lower()
        for word in inappropriate_words:
            if word in text_lower:
                return True
        
        return False
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize text input"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def _estimate_prompt_duration(self, prompt: str) -> float:
        """Estimate processing duration for prompt"""
        word_count = len(prompt.split())
        # Rough estimate: 2 seconds per word for AI processing
        return word_count * 2.0
    
    def _is_valid_file_content(self, file_path: str, file_type: str) -> bool:
        """Basic file content validation"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(512)  # Read first 512 bytes
                
                # Check file signatures
                if file_type == 'image':
                    return self._is_valid_image_header(header)
                elif file_type == 'video':
                    return self._is_valid_video_header(header)
                elif file_type == 'audio':
                    return self._is_valid_audio_header(header)
                else:
                    return True  # For documents, assume valid
                    
        except Exception:
            return False
    
    def _is_valid_image_header(self, header: bytes) -> bool:
        """Check if header matches image file signatures"""
        signatures = [
            b'\xFF\xD8\xFF',  # JPEG
            b'\x89PNG\r\n\x1A\n',  # PNG
            b'GIF87a',  # GIF
            b'GIF89a',  # GIF
            b'BM',  # BMP
        ]
        
        return any(header.startswith(sig) for sig in signatures)
    
    def _is_valid_video_header(self, header: bytes) -> bool:
        """Check if header matches video file signatures"""
        signatures = [
            b'\x00\x00\x00',  # MP4
            b'RIFF',  # AVI
            b'\x00\x00\x00\x18ftyp',  # MP4
        ]
        
        return any(header.startswith(sig) for sig in signatures)
    
    def _is_valid_audio_header(self, header: bytes) -> bool:
        """Check if header matches audio file signatures"""
        signatures = [
            b'ID3',  # MP3
            b'RIFF',  # WAV
            b'\xFF\xFB',  # MP3
        ]
        
        return any(header.startswith(sig) for sig in signatures)
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _sanitize_filename(self, file_path: str) -> str:
        """Sanitize filename"""
        filename = os.path.basename(file_path)
        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        return filename
    
    def _get_required_fields(self, endpoint: str) -> List[str]:
        """Get required fields for specific endpoint"""
        field_maps = {
            '/api/prompt': ['prompt'],
            '/api/approve': ['session_id', 'step_id', 'approved'],
            '/api/files/upload': ['file_path', 'file_type'],
            '/api/sessions': ['user_id']
        }
        return field_maps.get(endpoint, [])
    
    def _validate_field(self, field: str, value: Any, endpoint: str) -> List[str]:
        """Validate individual field"""
        errors = []
        
        # Type validation
        if field == 'prompt' and not isinstance(value, str):
            errors.append(f"Field {field} must be a string")
        elif field == 'session_id' and not isinstance(value, str):
            errors.append(f"Field {field} must be a string")
        elif field == 'approved' and not isinstance(value, bool):
            errors.append(f"Field {field} must be a boolean")
        
        # Value validation
        if field == 'prompt' and len(value) > 1000:
            errors.append(f"Field {field} too long")
        elif field == 'session_id' and not self._is_valid_session_id(value):
            errors.append(f"Field {field} has invalid format")
        
        return errors
    
    def _contains_suspicious_patterns(self, data: Dict[str, Any]) -> bool:
        """Check for suspicious patterns in request data"""
        data_str = str(data).lower()
        
        suspicious_patterns = [
            'union select',
            'drop table',
            'delete from',
            'insert into',
            'update set',
            'exec(',
            'eval(',
            'system(',
        ]
        
        return any(pattern in data_str for pattern in suspicious_patterns)
    
    def _sanitize_request_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize request data"""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self._sanitize_text(value)
            else:
                sanitized[key] = value
        return sanitized
    
    def _calculate_request_hash(self, data: Dict[str, Any]) -> str:
        """Calculate hash of request data"""
        data_str = str(sorted(data.items()))
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _is_valid_session_id(self, session_id: str) -> bool:
        """Validate session ID format"""
        # UUID format validation
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, session_id, re.IGNORECASE))
    
    def _is_valid_user_id(self, user_id: str) -> bool:
        """Validate user ID format"""
        # Alphanumeric with underscores and hyphens
        user_id_pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(user_id_pattern, user_id))
    
    def _is_valid_timestamp(self, timestamp: Any) -> bool:
        """Validate timestamp format"""
        try:
            if isinstance(timestamp, str):
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif isinstance(timestamp, (int, float)):
                datetime.fromtimestamp(timestamp)
            else:
                return False
            return True
        except (ValueError, TypeError):
            return False
    
    def _sanitize_session_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize session data"""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self._sanitize_text(value)
            else:
                sanitized[key] = value
        return sanitized

# Global input validator instance
input_validator = InputValidator() 