"""
File management with diff tracking and safe operations.
"""

import os
import shutil
import hashlib
import asyncio
import aiofiles
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class FileChange:
    """Represents a file change."""
    file_path: str
    change_type: str  # created, modified, deleted, moved
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    old_path: Optional[str] = None  # For moves
    timestamp: datetime = None
    size_change: int = 0
    line_changes: Dict[str, int] = None  # {"added": 10, "removed": 5}
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.line_changes is None:
            self.line_changes = {"added": 0, "removed": 0}


class FileManager:
    """Manages file operations with tracking and safety features."""
    
    def __init__(self, base_directory: str = "/tmp/agent_workspace"):
        self.base_directory = Path(base_directory)
        self.base_directory.mkdir(parents=True, exist_ok=True)
        
        # File change tracking
        self.file_changes: List[FileChange] = []
        self.file_hashes: Dict[str, str] = {}
        
        # Safety limits
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.max_files_per_operation = 100
        
        # Backup directory
        self.backup_directory = self.base_directory / ".backups"
        self.backup_directory.mkdir(exist_ok=True)
    
    async def read_file(self, file_path: str) -> str:
        """Read file contents."""
        
        full_path = self._resolve_path(file_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if full_path.stat().st_size > self.max_file_size:
            raise ValueError(f"File too large: {file_path}")
        
        try:
            async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            return content
        except UnicodeDecodeError:
            # Try with different encoding
            async with aiofiles.open(full_path, 'r', encoding='latin-1') as f:
                content = await f.read()
            return content
    
    async def write_file(
        self,
        file_path: str,
        content: str,
        create_backup: bool = True,
        mode: str = 'w'
    ) -> FileChange:
        """Write content to file."""
        
        full_path = self._resolve_path(file_path)
        
        # Check file size
        if len(content.encode('utf-8')) > self.max_file_size:
            raise ValueError(f"Content too large for file: {file_path}")
        
        # Read existing content for diff
        old_content = None
        change_type = "created"
        
        if full_path.exists():
            change_type = "modified"
            if create_backup:
                await self._create_backup(full_path)
            
            try:
                old_content = await self.read_file(file_path)
            except Exception:
                old_content = None
        
        # Create directory if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        async with aiofiles.open(full_path, mode, encoding='utf-8') as f:
            await f.write(content)
        
        # Calculate changes
        line_changes = self._calculate_line_changes(old_content, content)
        size_change = len(content.encode('utf-8'))
        if old_content:
            size_change -= len(old_content.encode('utf-8'))
        
        # Track change
        file_change = FileChange(
            file_path=str(full_path),
            change_type=change_type,
            old_content=old_content,
            new_content=content,
            size_change=size_change,
            line_changes=line_changes
        )
        
        self.file_changes.append(file_change)
        
        # Update file hash
        self.file_hashes[str(full_path)] = self._calculate_hash(content)
        
        return file_change
    
    async def append_to_file(self, file_path: str, content: str) -> FileChange:
        """Append content to file."""
        return await self.write_file(file_path, content, mode='a')
    
    async def delete_file(self, file_path: str, create_backup: bool = True) -> FileChange:
        """Delete a file."""
        
        full_path = self._resolve_path(file_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read content for tracking
        old_content = None
        try:
            old_content = await self.read_file(file_path)
        except Exception:
            pass
        
        # Create backup
        if create_backup:
            await self._create_backup(full_path)
        
        # Delete file
        full_path.unlink()
        
        # Track change
        file_change = FileChange(
            file_path=str(full_path),
            change_type="deleted",
            old_content=old_content,
            size_change=-len(old_content.encode('utf-8')) if old_content else 0
        )
        
        self.file_changes.append(file_change)
        
        # Remove from hash tracking
        self.file_hashes.pop(str(full_path), None)
        
        return file_change
    
    async def move_file(
        self,
        source_path: str,
        destination_path: str,
        create_backup: bool = True
    ) -> FileChange:
        """Move/rename a file."""
        
        source_full = self._resolve_path(source_path)
        dest_full = self._resolve_path(destination_path)
        
        if not source_full.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        if dest_full.exists():
            raise FileExistsError(f"Destination already exists: {destination_path}")
        
        # Read content for tracking
        content = None
        try:
            content = await self.read_file(source_path)
        except Exception:
            pass
        
        # Create backup
        if create_backup:
            await self._create_backup(source_full)
        
        # Create destination directory
        dest_full.parent.mkdir(parents=True, exist_ok=True)
        
        # Move file
        shutil.move(str(source_full), str(dest_full))
        
        # Track change
        file_change = FileChange(
            file_path=str(dest_full),
            change_type="moved",
            old_path=str(source_full),
            new_content=content
        )
        
        self.file_changes.append(file_change)
        
        # Update hash tracking
        old_hash = self.file_hashes.pop(str(source_full), None)
        if old_hash:
            self.file_hashes[str(dest_full)] = old_hash
        
        return file_change
    
    async def copy_file(
        self,
        source_path: str,
        destination_path: str,
        overwrite: bool = False
    ) -> FileChange:
        """Copy a file."""
        
        source_full = self._resolve_path(source_path)
        dest_full = self._resolve_path(destination_path)
        
        if not source_full.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        if dest_full.exists() and not overwrite:
            raise FileExistsError(f"Destination already exists: {destination_path}")
        
        # Read source content
        content = await self.read_file(source_path)
        
        # Write to destination
        return await self.write_file(destination_path, content)
    
    async def list_files(
        self,
        directory: str = ".",
        pattern: str = "*",
        recursive: bool = False
    ) -> List[Dict[str, Any]]:
        """List files in directory."""
        
        dir_path = self._resolve_path(directory)
        
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")
        
        files = []
        
        if recursive:
            pattern_path = dir_path.rglob(pattern)
        else:
            pattern_path = dir_path.glob(pattern)
        
        for file_path in pattern_path:
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "path": str(file_path.relative_to(self.base_directory)),
                    "name": file_path.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                    "is_directory": False,
                    "extension": file_path.suffix
                })
            elif file_path.is_dir():
                stat = file_path.stat()
                files.append({
                    "path": str(file_path.relative_to(self.base_directory)),
                    "name": file_path.name,
                    "size": 0,
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                    "is_directory": True,
                    "extension": ""
                })
        
        return sorted(files, key=lambda x: (x["is_directory"], x["name"]))
    
    async def create_directory(self, directory_path: str) -> bool:
        """Create a directory."""
        
        dir_path = self._resolve_path(directory_path)
        
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Failed to create directory: {e}")
            return False
    
    async def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get detailed file information."""
        
        full_path = self._resolve_path(file_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        stat = full_path.stat()
        
        info = {
            "path": str(full_path),
            "name": full_path.name,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime),
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "accessed": datetime.fromtimestamp(stat.st_atime),
            "is_directory": full_path.is_dir(),
            "is_file": full_path.is_file(),
            "extension": full_path.suffix,
            "permissions": oct(stat.st_mode)[-3:]
        }
        
        # Add content hash if it's a file
        if full_path.is_file() and stat.st_size <= self.max_file_size:
            try:
                content = await self.read_file(file_path)
                info["hash"] = self._calculate_hash(content)
                info["line_count"] = len(content.splitlines())
            except Exception:
                info["hash"] = None
                info["line_count"] = 0
        
        return info
    
    def get_changes(self, since: Optional[datetime] = None) -> List[FileChange]:
        """Get file changes since a specific time."""
        
        if since is None:
            return self.file_changes.copy()
        
        return [
            change for change in self.file_changes
            if change.timestamp >= since
        ]
    
    def clear_changes(self) -> None:
        """Clear change history."""
        self.file_changes.clear()
    
    async def _create_backup(self, file_path: Path) -> None:
        """Create a backup of a file."""
        
        if not file_path.exists():
            return
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.{timestamp}.backup"
        backup_path = self.backup_directory / backup_name
        
        try:
            shutil.copy2(str(file_path), str(backup_path))
        except Exception as e:
            print(f"Failed to create backup: {e}")
    
    def _resolve_path(self, file_path: str) -> Path:
        """Resolve file path relative to base directory."""
        
        path = Path(file_path)
        
        if path.is_absolute():
            # Ensure path is within base directory for security
            try:
                path.resolve().relative_to(self.base_directory.resolve())
                return path
            except ValueError:
                # Path is outside base directory, make it relative
                return self.base_directory / path.name
        else:
            return self.base_directory / path
    
    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _calculate_line_changes(
        self,
        old_content: Optional[str],
        new_content: str
    ) -> Dict[str, int]:
        """Calculate line changes between old and new content."""
        
        if old_content is None:
            return {
                "added": len(new_content.splitlines()),
                "removed": 0
            }
        
        old_lines = set(old_content.splitlines())
        new_lines = set(new_content.splitlines())
        
        added = len(new_lines - old_lines)
        removed = len(old_lines - new_lines)
        
        return {"added": added, "removed": removed}
    
    async def search_in_files(
        self,
        pattern: str,
        directory: str = ".",
        file_pattern: str = "*",
        case_sensitive: bool = False
    ) -> List[Dict[str, Any]]:
        """Search for pattern in files."""
        
        import re
        
        results = []
        files = await self.list_files(directory, file_pattern, recursive=True)
        
        # Compile regex pattern
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            regex = re.compile(pattern, flags)
        except re.error:
            # If pattern is not valid regex, treat as literal string
            regex = re.compile(re.escape(pattern), flags)
        
        for file_info in files:
            if file_info["is_directory"]:
                continue
            
            try:
                content = await self.read_file(file_info["path"])
                lines = content.splitlines()
                
                matches = []
                for line_num, line in enumerate(lines, 1):
                    if regex.search(line):
                        matches.append({
                            "line_number": line_num,
                            "line_content": line.strip(),
                            "match_start": regex.search(line).start(),
                            "match_end": regex.search(line).end()
                        })
                
                if matches:
                    results.append({
                        "file": file_info["path"],
                        "matches": matches,
                        "total_matches": len(matches)
                    })
                    
            except Exception as e:
                # Skip files that can't be read
                continue
        
        return results