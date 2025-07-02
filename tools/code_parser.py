"""
Code parsing and AST analysis using tree-sitter.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class ASTNode:
    """Represents an AST node."""
    type: str
    name: Optional[str] = None
    start_line: int = 0
    end_line: int = 0
    children: List['ASTNode'] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.metadata is None:
            self.metadata = {}


class CodeParser:
    """Code parser using tree-sitter for AST analysis."""
    
    def __init__(self):
        self.parsers = {}
        self._initialize_parsers()
    
    def _initialize_parsers(self):
        """Initialize tree-sitter parsers for different languages."""
        # This would normally initialize tree-sitter parsers
        # For now, we'll use a simple fallback implementation
        self.supported_languages = {
            'python': '.py',
            'javascript': '.js',
            'typescript': '.ts',
            'java': '.java',
            'cpp': '.cpp',
            'c': '.c',
            'go': '.go',
            'rust': '.rs'
        }
    
    def parse_code(self, code: str, language: str) -> Optional[ASTNode]:
        """Parse code and return AST."""
        
        if language not in self.supported_languages:
            return None
        
        # Simple fallback parser for Python
        if language == 'python':
            return self._parse_python_simple(code)
        
        # For other languages, return a basic structure
        return ASTNode(
            type="module",
            name="root",
            start_line=1,
            end_line=len(code.splitlines()),
            metadata={"language": language}
        )
    
    def _parse_python_simple(self, code: str) -> ASTNode:
        """Simple Python parser fallback."""
        
        lines = code.splitlines()
        root = ASTNode(type="module", name="root", start_line=1, end_line=len(lines))
        
        current_class = None
        current_function = None
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            if stripped.startswith('class '):
                class_name = stripped.split()[1].split('(')[0].rstrip(':')
                current_class = ASTNode(
                    type="class",
                    name=class_name,
                    start_line=i,
                    end_line=i
                )
                root.children.append(current_class)
                current_function = None
            
            elif stripped.startswith('def '):
                func_name = stripped.split()[1].split('(')[0]
                func_node = ASTNode(
                    type="function",
                    name=func_name,
                    start_line=i,
                    end_line=i
                )
                
                if current_class:
                    current_class.children.append(func_node)
                else:
                    root.children.append(func_node)
                
                current_function = func_node
            
            elif stripped.startswith('import ') or stripped.startswith('from '):
                import_node = ASTNode(
                    type="import",
                    name=stripped,
                    start_line=i,
                    end_line=i
                )
                root.children.append(import_node)
        
        return root
    
    def extract_functions(self, ast: ASTNode) -> List[ASTNode]:
        """Extract all function definitions from AST."""
        
        functions = []
        
        def traverse(node):
            if node.type == "function":
                functions.append(node)
            
            for child in node.children:
                traverse(child)
        
        traverse(ast)
        return functions
    
    def extract_classes(self, ast: ASTNode) -> List[ASTNode]:
        """Extract all class definitions from AST."""
        
        classes = []
        
        def traverse(node):
            if node.type == "class":
                classes.append(node)
            
            for child in node.children:
                traverse(child)
        
        traverse(ast)
        return classes
    
    def find_node_by_name(self, ast: ASTNode, name: str) -> Optional[ASTNode]:
        """Find a node by name in the AST."""
        
        def traverse(node):
            if node.name == name:
                return node
            
            for child in node.children:
                result = traverse(child)
                if result:
                    return result
            
            return None
        
        return traverse(ast)
    
    def get_code_metrics(self, ast: ASTNode) -> Dict[str, int]:
        """Get basic code metrics from AST."""
        
        metrics = {
            "functions": 0,
            "classes": 0,
            "imports": 0,
            "total_nodes": 0
        }
        
        def traverse(node):
            metrics["total_nodes"] += 1
            
            if node.type == "function":
                metrics["functions"] += 1
            elif node.type == "class":
                metrics["classes"] += 1
            elif node.type == "import":
                metrics["imports"] += 1
            
            for child in node.children:
                traverse(child)
        
        traverse(ast)
        return metrics