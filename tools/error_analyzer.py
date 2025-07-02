"""
Error analysis and reporting tools.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re


@dataclass
class ErrorReport:
    """Represents an error analysis report."""
    error_type: str
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    stack_trace: Optional[str] = None
    suggested_fixes: List[str] = None
    
    def __post_init__(self):
        if self.suggested_fixes is None:
            self.suggested_fixes = []


class ErrorAnalyzer:
    """Analyzes errors and provides insights."""
    
    def __init__(self):
        self.error_patterns = {
            "python": {
                "SyntaxError": r"SyntaxError: (.+)",
                "NameError": r"NameError: (.+)",
                "TypeError": r"TypeError: (.+)",
                "AttributeError": r"AttributeError: (.+)",
                "ImportError": r"ImportError: (.+)",
                "IndexError": r"IndexError: (.+)",
                "KeyError": r"KeyError: (.+)"
            }
        }
    
    def analyze_error(self, error_text: str, language: str = "python") -> ErrorReport:
        """Analyze an error and create a report."""
        
        error_type = self._extract_error_type(error_text, language)
        message = self._extract_error_message(error_text, language)
        file_path, line_number = self._extract_location(error_text)
        stack_trace = self._extract_stack_trace(error_text)
        
        return ErrorReport(
            error_type=error_type,
            message=message,
            file_path=file_path,
            line_number=line_number,
            stack_trace=stack_trace,
            suggested_fixes=self._suggest_fixes(error_type, message)
        )
    
    def _extract_error_type(self, error_text: str, language: str) -> str:
        """Extract error type from error text."""
        
        if language in self.error_patterns:
            for error_type, pattern in self.error_patterns[language].items():
                if re.search(pattern, error_text):
                    return error_type
        
        return "UnknownError"
    
    def _extract_error_message(self, error_text: str, language: str) -> str:
        """Extract error message."""
        
        lines = error_text.strip().split('\n')
        if lines:
            return lines[-1]  # Usually the last line contains the error message
        
        return error_text
    
    def _extract_location(self, error_text: str) -> tuple:
        """Extract file path and line number."""
        
        # Look for file and line patterns
        file_pattern = r'File "([^"]+)", line (\d+)'
        match = re.search(file_pattern, error_text)
        
        if match:
            return match.group(1), int(match.group(2))
        
        return None, None
    
    def _extract_stack_trace(self, error_text: str) -> Optional[str]:
        """Extract stack trace."""
        
        if "Traceback" in error_text:
            return error_text
        
        return None
    
    def _suggest_fixes(self, error_type: str, message: str) -> List[str]:
        """Suggest fixes based on error type."""
        
        fixes = []
        
        if error_type == "SyntaxError":
            fixes.append("Check for missing parentheses, brackets, or quotes")
            fixes.append("Verify proper indentation")
            fixes.append("Look for typos in keywords")
        
        elif error_type == "NameError":
            fixes.append("Check if the variable is defined before use")
            fixes.append("Verify correct spelling of variable names")
            fixes.append("Check if imports are missing")
        
        elif error_type == "TypeError":
            fixes.append("Check data types being used")
            fixes.append("Verify function arguments match expected types")
            fixes.append("Look for None values where objects are expected")
        
        elif error_type == "ImportError":
            fixes.append("Check if the module is installed")
            fixes.append("Verify the module name spelling")
            fixes.append("Check Python path and virtual environment")
        
        return fixes