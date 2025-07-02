"""
Conversation memory management for chat history and context.
"""

import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .vector_memory import VectorMemory


@dataclass
class ConversationMessage:
    """Represents a conversation message."""
    id: str
    conversation_id: str
    role: str  # user, assistant, system
    content: str
    timestamp: datetime
    metadata: Dict[str, Any]


class ConversationMemory:
    """Manages conversation history and context."""
    
    def __init__(self, memory: VectorMemory):
        self.memory = memory
        self.active_conversations: Dict[str, List[ConversationMessage]] = {}
    
    async def start_conversation(self, conversation_id: str = None) -> str:
        """Start a new conversation."""
        
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())
        
        self.active_conversations[conversation_id] = []
        
        # Store conversation start in memory
        await self.memory.store_text(
            text=f"Conversation started: {conversation_id}",
            metadata={
                "type": "conversation_start",
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return conversation_id
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> ConversationMessage:
        """Add a message to the conversation."""
        
        message = ConversationMessage(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        # Add to active conversation
        if conversation_id not in self.active_conversations:
            self.active_conversations[conversation_id] = []
        
        self.active_conversations[conversation_id].append(message)
        
        # Store in vector memory
        await self.memory.store_text(
            text=f"{role}: {content}",
            metadata={
                "type": "conversation_message",
                "conversation_id": conversation_id,
                "message_id": message.id,
                "role": role,
                "timestamp": message.timestamp.isoformat(),
                **message.metadata
            }
        )
        
        return message
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50
    ) -> List[ConversationMessage]:
        """Get conversation history."""
        
        # First check active conversations
        if conversation_id in self.active_conversations:
            messages = self.active_conversations[conversation_id]
            return messages[-limit:] if limit else messages
        
        # Load from memory
        results = await self.memory.search_by_metadata(
            filter_metadata={
                "type": "conversation_message",
                "conversation_id": conversation_id
            },
            limit=limit
        )
        
        # Convert to ConversationMessage objects
        messages = []
        for result in results:
            metadata = result.metadata
            
            # Parse content to extract role and message
            content_parts = result.text.split(": ", 1)
            if len(content_parts) == 2:
                role, content = content_parts
            else:
                role = metadata.get("role", "unknown")
                content = result.text
            
            message = ConversationMessage(
                id=metadata.get("message_id", result.id),
                conversation_id=conversation_id,
                role=role,
                content=content,
                timestamp=datetime.fromisoformat(metadata.get("timestamp", datetime.now().isoformat())),
                metadata=metadata
            )
            messages.append(message)
        
        # Sort by timestamp
        messages.sort(key=lambda x: x.timestamp)
        
        # Cache in active conversations
        self.active_conversations[conversation_id] = messages
        
        return messages
    
    async def search_conversations(
        self,
        query: str,
        conversation_id: str = None,
        limit: int = 10
    ) -> List[ConversationMessage]:
        """Search for messages in conversations."""
        
        filter_metadata = {"type": "conversation_message"}
        if conversation_id:
            filter_metadata["conversation_id"] = conversation_id
        
        results = await self.memory.search(
            query=query,
            limit=limit,
            filter_metadata=filter_metadata
        )
        
        # Convert to ConversationMessage objects
        messages = []
        for result in results:
            metadata = result.metadata
            
            content_parts = result.text.split(": ", 1)
            if len(content_parts) == 2:
                role, content = content_parts
            else:
                role = metadata.get("role", "unknown")
                content = result.text
            
            message = ConversationMessage(
                id=metadata.get("message_id", result.id),
                conversation_id=metadata.get("conversation_id", "unknown"),
                role=role,
                content=content,
                timestamp=datetime.fromisoformat(metadata.get("timestamp", datetime.now().isoformat())),
                metadata=metadata
            )
            messages.append(message)
        
        return messages
    
    async def get_conversation_summary(self, conversation_id: str) -> str:
        """Get a summary of the conversation."""
        
        messages = await self.get_conversation_history(conversation_id)
        
        if not messages:
            return "No messages in conversation"
        
        # Create basic summary
        user_messages = [m for m in messages if m.role == "user"]
        assistant_messages = [m for m in messages if m.role == "assistant"]
        
        summary = f"""
Conversation Summary (ID: {conversation_id})
- Total messages: {len(messages)}
- User messages: {len(user_messages)}
- Assistant messages: {len(assistant_messages)}
- Started: {messages[0].timestamp.strftime('%Y-%m-%d %H:%M:%S')}
- Last activity: {messages[-1].timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Add recent topics (simple keyword extraction)
        recent_content = " ".join([m.content for m in messages[-5:]])
        words = recent_content.lower().split()
        word_freq = {}
        
        for word in words:
            if len(word) > 3 and word.isalpha():
                word_freq[word] = word_freq.get(word, 0) + 1
        
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        if top_words:
            summary += f"\nRecent topics: {', '.join([word for word, _ in top_words])}"
        
        return summary
    
    async def end_conversation(self, conversation_id: str) -> None:
        """End a conversation and clean up."""
        
        # Store conversation end in memory
        await self.memory.store_text(
            text=f"Conversation ended: {conversation_id}",
            metadata={
                "type": "conversation_end",
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Remove from active conversations
        if conversation_id in self.active_conversations:
            del self.active_conversations[conversation_id]
    
    def get_active_conversations(self) -> List[str]:
        """Get list of active conversation IDs."""
        return list(self.active_conversations.keys())
    
    async def cleanup_old_conversations(self, days: int = 30) -> int:
        """Clean up conversations older than specified days."""
        
        # This would implement cleanup logic
        # For now, just return 0
        return 0