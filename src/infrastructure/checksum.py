"""
Checksum utility for row-level integrity and versioning.
"""
import hashlib
import json
from typing import Any, Dict


def calculate_checksum(data: Dict[str, Any]) -> str:
    """
    Calculate SHA256 checksum of data for integrity verification.
    
    Args:
        data: Dictionary of field values to hash
        
    Returns:
        SHA256 hex digest (first 16 chars for brevity in DB)
    """
    # Exclude metadata fields from checksum
    exclude_fields = {'version', 'checksum', 'timestamp_criacao', 'timestamp_atualizacao'}
    
    filtered_data = {
        k: v for k, v in sorted(data.items())
        if k not in exclude_fields and v is not None
    }
    
    # Convert to JSON string for consistent hashing
    json_str = json.dumps(filtered_data, default=str, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]


def verify_checksum(data: Dict[str, Any], stored_checksum: str) -> bool:
    """
    Verify that data matches the stored checksum.
    
    Args:
        data: Current field values
        stored_checksum: Previously calculated checksum
        
    Returns:
        True if checksums match
    """
    current_checksum = calculate_checksum(data)
    return current_checksum == stored_checksum
