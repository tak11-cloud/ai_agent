"""
Prompt building system with ReAct templates and dynamic assembly.
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from jinja2 import Template


@dataclass
class ReActStep:
    """Single step in ReAct reasoning."""
    observation: str
    thought: str
    action: str
    action_input: Dict[str, Any]
    result: Optional[str] = None


class ReActPrompt:
    """ReAct (Reasoning + Acting) prompt builder."""
    
    REACT_TEMPLATE = """You are an autonomous AI agent with reasoning and action capabilities.

SYSTEM CONTEXT:
{{ system_context }}

AVAILABLE TOOLS:
{% for tool in tools %}
- {{ tool.name }}: {{ tool.description }}
  Parameters: {{ tool.parameters }}
{% endfor %}

CONVERSATION HISTORY:
{% for msg in conversation_history %}
{{ msg.role }}: {{ msg.content }}
{% endfor %}

CURRENT TASK:
{{ task }}

REASONING FORMAT:
Use this exact format for your response:

Observation: [What you observe about the current situation]
Thought: [Your reasoning about what to do next]
Action: [The action you want to take]
Action Input: [JSON parameters for the action]

PREVIOUS STEPS:
{% for step in previous_steps %}
Observation: {{ step.observation }}
Thought: {{ step.thought }}
Action: {{ step.action }}
Action Input: {{ step.action_input }}
Result: {{ step.result }}
{% endfor %}

Now continue with your next step:

Observation: [Analyze the current state]
Thought: [Reason about what to do]
Action: [Choose an action]
Action Input: [Provide parameters]"""

    def __init__(self):
        self.template = Template(self.REACT_TEMPLATE)
    
    def build(
        self,
        task: str,
        tools: List[Dict[str, Any]],
        system_context: str = "",
        conversation_history: List[Dict[str, str]] = None,
        previous_steps: List[ReActStep] = None
    ) -> str:
        """Build a ReAct prompt."""
        return self.template.render(
            task=task,
            tools=tools or [],
            system_context=system_context,
            conversation_history=conversation_history or [],
            previous_steps=previous_steps or []
        )


class PromptBuilder:
    """Advanced prompt builder with templates and context injection."""
    
    def __init__(self):
        self.templates: Dict[str, Template] = {}
        self.load_default_templates()
    
    def load_default_templates(self):
        """Load default prompt templates."""
        
        # Code generation template
        self.templates["code_generation"] = Template("""
You are an expert software engineer. Generate high-quality code based on the requirements.

CONTEXT:
{{ context }}

REQUIREMENTS:
{{ requirements }}

EXISTING CODE:
```{{ language }}
{{ existing_code }}
```

CONSTRAINTS:
- Follow best practices for {{ language }}
- Include proper error handling
- Add minimal but clear comments
- Ensure code is production-ready

Generate the code:
""")
        
        # Bug fixing template
        self.templates["bug_fix"] = Template("""
You are a debugging expert. Analyze the error and provide a fix.

ERROR DETAILS:
{{ error_message }}

STACK TRACE:
{{ stack_trace }}

PROBLEMATIC CODE:
```{{ language }}
{{ code }}
```

CONTEXT:
{{ context }}

Provide:
1. Root cause analysis
2. Specific fix
3. Prevention strategy

Fix:
""")
        
        # Test generation template
        self.templates["test_generation"] = Template("""
You are a test automation expert. Generate comprehensive tests.

CODE TO TEST:
```{{ language }}
{{ code }}
```

REQUIREMENTS:
- Test all public methods/functions
- Include edge cases and error conditions
- Use appropriate testing framework
- Ensure good test coverage

Generate tests:
""")
        
        # Planning template
        self.templates["task_planning"] = Template("""
You are a project planning expert. Break down the task into actionable steps.

TASK:
{{ task }}

CONTEXT:
{{ context }}

CONSTRAINTS:
{{ constraints }}

Create a detailed plan with:
1. Clear, actionable steps
2. Dependencies between steps
3. Estimated effort
4. Success criteria

Plan:
""")
    
    def build_prompt(
        self,
        template_name: str,
        **kwargs
    ) -> str:
        """Build a prompt from template."""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        return self.templates[template_name].render(**kwargs)
    
    def add_template(self, name: str, template_str: str):
        """Add a custom template."""
        self.templates[name] = Template(template_str)
    
    def build_function_calling_prompt(
        self,
        task: str,
        functions: List[Dict[str, Any]],
        context: str = ""
    ) -> str:
        """Build a function calling prompt."""
        
        functions_str = json.dumps(functions, indent=2)
        
        prompt = f"""You are an AI assistant with access to functions. Use them to complete tasks.

TASK: {task}

CONTEXT: {context}

AVAILABLE FUNCTIONS:
{functions_str}

INSTRUCTIONS:
1. Analyze the task and determine which functions to call
2. Call functions in the correct order
3. Use the results to complete the task
4. Provide a final summary

Respond with function calls in this format:
```json
{{
  "function": "function_name",
  "parameters": {{
    "param1": "value1",
    "param2": "value2"
  }}
}}
```

Begin:"""
        
        return prompt
    
    def inject_context(
        self,
        prompt: str,
        context: Dict[str, Any]
    ) -> str:
        """Inject context into a prompt."""
        template = Template(prompt)
        return template.render(**context)
    
    def build_chat_prompt(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = ""
    ) -> str:
        """Build a chat-style prompt."""
        
        prompt_parts = []
        
        if system_prompt:
            prompt_parts.append(f"SYSTEM: {system_prompt}")
        
        for msg in messages:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            prompt_parts.append(f"{role}: {content}")
        
        prompt_parts.append("ASSISTANT:")
        
        return "\n\n".join(prompt_parts)