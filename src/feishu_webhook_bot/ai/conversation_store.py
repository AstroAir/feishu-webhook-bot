"""Persistent conversation storage using SQLAlchemy.

This module provides database-backed conversation persistence with automatic
cleanup of old data, token tracking, and message history management.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, relationship

from ..core.logger import get_logger

logger = get_logger("ai.conversation_store")


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for ORM models."""

    pass


class ConversationRecord(Base):
    """Persistent conversation record.

    Attributes:
        id: Primary key
        user_key: Unique user identifier (platform:chat_type:sender_id)
        platform: Platform name (feishu, qq, etc.)
        chat_id: Chat or group ID
        created_at: Timestamp when conversation was created
        last_activity: Timestamp of last activity
        summary: Optional conversation summary
        total_tokens: Total tokens used in conversation
        message_count: Total number of messages
        messages: Related message records
    """

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_key = Column(String(255), index=True, nullable=False)
    platform = Column(String(50), nullable=False)
    chat_id = Column(String(255), index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    last_activity = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    summary = Column(Text, nullable=True)
    total_tokens = Column(Integer, default=0)
    message_count = Column(Integer, default=0)

    messages = relationship(
        "MessageRecord",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "id": self.id,
            "user_key": self.user_key,
            "platform": self.platform,
            "chat_id": self.chat_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "summary": self.summary,
            "total_tokens": self.total_tokens,
            "message_count": self.message_count,
        }


class MessageRecord(Base):
    """Individual message in a conversation.

    Attributes:
        id: Primary key
        conversation_id: Foreign key to conversation
        role: Message role (user, assistant, system, tool)
        content: Message content
        timestamp: Timestamp when message was created
        tokens: Token count for this message
        metadata_json: JSON metadata (tool calls, etc.)
        conversation: Related conversation record
    """

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))
    tokens = Column(Integer, default=0)
    metadata_json = Column(Text, nullable=True)

    conversation = relationship("ConversationRecord", back_populates="messages")

    def get_metadata(self) -> dict[str, Any]:
        """Get parsed metadata."""
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except json.JSONDecodeError:
            logger.warning("Failed to parse metadata JSON for message %d", self.id)
            return {}

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "tokens": self.tokens,
            "metadata": self.get_metadata(),
        }


class PersistentConversationManager:
    """Database-backed conversation manager.

    Provides persistent storage for conversations and messages with automatic
    cleanup of old data.

    Example:
        ```python
        manager = PersistentConversationManager("sqlite:///conversations.db")

        # Get or create conversation
        conv = manager.get_or_create("feishu:group:user123", "feishu", "chat456")

        # Save messages
        manager.save_message(conv.id, "user", "Hello!")
        manager.save_message(conv.id, "assistant", "Hi there!")

        # Load history
        history = manager.load_history(conv.id, max_turns=10)
        ```
    """

    def __init__(
        self,
        db_url: str | None = None,
        echo: bool = False,
        data_dir: str | None = None,
    ) -> None:
        """Initialize the persistent conversation manager.

        Args:
            db_url: SQLAlchemy database URL. If None, uses SQLite in data_dir.
            echo: Enable SQL logging
            data_dir: Directory for SQLite database (if db_url is None)

        Raises:
            ValueError: If database cannot be initialized
        """
        if db_url is None:
            if data_dir is None:
                data_dir = "data"
            data_path = Path(data_dir)
            data_path.mkdir(parents=True, exist_ok=True)
            db_url = f"sqlite:///{data_path / 'conversations.db'}"

        try:
            self.engine = create_engine(db_url, echo=echo, connect_args={"check_same_thread": False})
            Base.metadata.create_all(self.engine)
            logger.info("Initialized conversation store with database: %s", db_url)
        except Exception as exc:
            logger.error("Failed to initialize conversation store: %s", exc, exc_info=True)
            raise ValueError(f"Failed to initialize conversation database: {str(exc)}") from exc

    def get_session(self) -> Session:
        """Get a database session.

        Returns:
            SQLAlchemy Session instance
        """
        return Session(self.engine)

    def get_or_create(
        self,
        user_key: str,
        platform: str,
        chat_id: str | None = None,
    ) -> ConversationRecord:
        """Get existing conversation or create new one.

        Args:
            user_key: Unique user identifier (platform:chat_type:sender_id)
            platform: Platform name (feishu, qq)
            chat_id: Chat/group ID

        Returns:
            ConversationRecord instance
        """
        session = self.get_session()
        try:
            # Try to find existing conversation
            conv = session.query(ConversationRecord).filter_by(user_key=user_key).first()

            if conv is not None:
                logger.debug("Retrieved existing conversation for user: %s", user_key)
                session.close()
                return conv

            # Create new conversation
            conv = ConversationRecord(
                user_key=user_key,
                platform=platform,
                chat_id=chat_id,
                created_at=datetime.now(UTC),
                last_activity=datetime.now(UTC),
            )
            session.add(conv)
            session.commit()
            conv_id = conv.id
            session.close()

            logger.info("Created new conversation for user: %s (id=%d)", user_key, conv_id)

            # Retrieve the created conversation
            session = self.get_session()
            conv = session.query(ConversationRecord).filter_by(id=conv_id).first()
            session.close()
            return conv

        except Exception as exc:
            session.rollback()
            session.close()
            logger.error("Failed to get or create conversation: %s", exc, exc_info=True)
            raise

    def save_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        tokens: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> MessageRecord:
        """Save a message to the conversation.

        Args:
            conversation_id: ID of the conversation
            role: Message role (user, assistant, system, tool)
            content: Message content
            tokens: Token count for this message
            metadata: Additional metadata as dict

        Returns:
            Created MessageRecord

        Raises:
            ValueError: If conversation not found
        """
        session = self.get_session()
        try:
            # Verify conversation exists
            conv = session.query(ConversationRecord).filter_by(id=conversation_id).first()
            if conv is None:
                raise ValueError(f"Conversation not found: {conversation_id}")

            # Create message
            metadata_json = json.dumps(metadata) if metadata else None
            message = MessageRecord(
                conversation_id=conversation_id,
                role=role,
                content=content,
                tokens=tokens,
                metadata_json=metadata_json,
                timestamp=datetime.now(UTC),
            )

            session.add(message)
            # Update conversation stats
            conv.last_activity = datetime.now(UTC)
            conv.message_count += 1
            conv.total_tokens += tokens

            session.commit()
            message_id = message.id

            logger.debug(
                "Saved message %d to conversation %d (role=%s, tokens=%d)",
                message_id,
                conversation_id,
                role,
                tokens,
            )

            session.close()
            return message

        except Exception as exc:
            session.rollback()
            session.close()
            logger.error("Failed to save message: %s", exc, exc_info=True)
            raise

    def load_history(
        self,
        conversation_id: int,
        max_turns: int = 10,
    ) -> list[dict[str, Any]]:
        """Load conversation history.

        Args:
            conversation_id: ID of the conversation
            max_turns: Maximum number of turns (user+assistant pairs) to load

        Returns:
            List of message dicts with role and content

        Raises:
            ValueError: If conversation not found
        """
        session = self.get_session()
        try:
            conv = session.query(ConversationRecord).filter_by(id=conversation_id).first()
            if conv is None:
                raise ValueError(f"Conversation not found: {conversation_id}")

            # Load messages
            messages = session.query(MessageRecord).filter_by(conversation_id=conversation_id).all()

            # Limit to max_turns (each turn is roughly 2 messages)
            max_messages = max_turns * 2
            if len(messages) > max_messages:
                messages = messages[-max_messages:]

            result = [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                    "tokens": msg.tokens,
                }
                for msg in messages
            ]

            logger.debug(
                "Loaded %d messages from conversation %d (requested max_turns=%d)",
                len(result),
                conversation_id,
                max_turns,
            )

            session.close()
            return result

        except Exception as exc:
            session.rollback()
            session.close()
            logger.error("Failed to load conversation history: %s", exc, exc_info=True)
            raise

    def get_conversation_by_user(
        self,
        user_key: str,
    ) -> ConversationRecord | None:
        """Get the most recent conversation for a user.

        Args:
            user_key: Unique user identifier

        Returns:
            ConversationRecord or None if not found
        """
        session = self.get_session()
        try:
            conv = (
                session.query(ConversationRecord)
                .filter_by(user_key=user_key)
                .order_by(ConversationRecord.last_activity.desc())
                .first()
            )

            logger.debug("Retrieved conversation for user: %s (found=%s)", user_key, conv is not None)

            session.close()
            return conv

        except Exception as exc:
            session.rollback()
            session.close()
            logger.error("Failed to get conversation by user: %s", exc, exc_info=True)
            raise

    def update_conversation_stats(
        self,
        conversation_id: int,
        tokens_used: int,
    ) -> None:
        """Update conversation statistics after AI response.

        Args:
            conversation_id: ID of the conversation
            tokens_used: Tokens used in this update

        Raises:
            ValueError: If conversation not found
        """
        session = self.get_session()
        try:
            conv = session.query(ConversationRecord).filter_by(id=conversation_id).first()
            if conv is None:
                raise ValueError(f"Conversation not found: {conversation_id}")

            conv.total_tokens += tokens_used
            conv.last_activity = datetime.now(UTC)
            session.commit()

            logger.debug(
                "Updated conversation %d stats (added tokens=%d, total=%d)",
                conversation_id,
                tokens_used,
                conv.total_tokens,
            )

            session.close()

        except Exception as exc:
            session.rollback()
            session.close()
            logger.error("Failed to update conversation stats: %s", exc, exc_info=True)
            raise

    def clear_conversation(
        self,
        conversation_id: int,
    ) -> None:
        """Clear all messages from a conversation (keep record).

        Args:
            conversation_id: ID of the conversation

        Raises:
            ValueError: If conversation not found
        """
        session = self.get_session()
        try:
            conv = session.query(ConversationRecord).filter_by(id=conversation_id).first()
            if conv is None:
                raise ValueError(f"Conversation not found: {conversation_id}")

            # Delete messages
            session.query(MessageRecord).filter_by(conversation_id=conversation_id).delete()

            # Reset stats
            conv.message_count = 0
            conv.total_tokens = 0
            conv.summary = None
            conv.last_activity = datetime.now(UTC)

            session.commit()

            logger.info("Cleared conversation %d", conversation_id)

            session.close()

        except Exception as exc:
            session.rollback()
            session.close()
            logger.error("Failed to clear conversation: %s", exc, exc_info=True)
            raise

    def delete_conversation(
        self,
        conversation_id: int,
    ) -> None:
        """Delete a conversation and all its messages.

        Args:
            conversation_id: ID of the conversation

        Raises:
            ValueError: If conversation not found
        """
        session = self.get_session()
        try:
            conv = session.query(ConversationRecord).filter_by(id=conversation_id).first()
            if conv is None:
                raise ValueError(f"Conversation not found: {conversation_id}")

            session.delete(conv)
            session.commit()

            logger.info("Deleted conversation %d", conversation_id)

            session.close()

        except Exception as exc:
            session.rollback()
            session.close()
            logger.error("Failed to delete conversation: %s", exc, exc_info=True)
            raise

    def cleanup_old_conversations(
        self,
        days: int = 30,
    ) -> int:
        """Delete conversations older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            Number of conversations deleted
        """
        session = self.get_session()
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days)

            # Find old conversations
            old_convs = (
                session.query(ConversationRecord)
                .filter(ConversationRecord.last_activity < cutoff_date)
                .all()
            )

            count = len(old_convs)

            # Delete them
            for conv in old_convs:
                session.delete(conv)

            session.commit()

            logger.info(
                "Cleaned up %d conversations older than %d days", count, days
            )

            session.close()
            return count

        except Exception as exc:
            session.rollback()
            session.close()
            logger.error("Failed to cleanup old conversations: %s", exc, exc_info=True)
            raise

    def export_conversation(
        self,
        conversation_id: int,
    ) -> dict[str, Any]:
        """Export conversation to dict for backup/transfer.

        Args:
            conversation_id: ID of the conversation

        Returns:
            Dictionary representation of the conversation

        Raises:
            ValueError: If conversation not found
        """
        session = self.get_session()
        try:
            conv = session.query(ConversationRecord).filter_by(id=conversation_id).first()
            if conv is None:
                raise ValueError(f"Conversation not found: {conversation_id}")

            messages = session.query(MessageRecord).filter_by(conversation_id=conversation_id).all()

            data = {
                "conversation": conv.to_dict(),
                "messages": [msg.to_dict() for msg in messages],
            }

            logger.info("Exported conversation %d", conversation_id)

            session.close()
            return data

        except Exception as exc:
            session.rollback()
            session.close()
            logger.error("Failed to export conversation: %s", exc, exc_info=True)
            raise

    def import_conversation(
        self,
        data: dict[str, Any],
    ) -> ConversationRecord:
        """Import conversation from exported data.

        Args:
            data: Dictionary representation of the conversation

        Returns:
            Created ConversationRecord

        Raises:
            ValueError: If data is invalid
        """
        session = self.get_session()
        try:
            conv_data = data.get("conversation")
            if not conv_data:
                raise ValueError("Missing 'conversation' key in import data")

            # Check if conversation already exists
            existing = session.query(ConversationRecord).filter_by(
                user_key=conv_data["user_key"]
            ).first()

            if existing:
                logger.warning(
                    "Conversation already exists for user: %s", conv_data["user_key"]
                )
                session.close()
                return existing

            # Create new conversation
            conv = ConversationRecord(
                user_key=conv_data["user_key"],
                platform=conv_data["platform"],
                chat_id=conv_data.get("chat_id"),
                summary=conv_data.get("summary"),
                total_tokens=conv_data.get("total_tokens", 0),
                message_count=conv_data.get("message_count", 0),
            )

            # Parse timestamps
            if "created_at" in conv_data:
                conv.created_at = datetime.fromisoformat(conv_data["created_at"])
            if "last_activity" in conv_data:
                conv.last_activity = datetime.fromisoformat(conv_data["last_activity"])

            session.add(conv)
            session.flush()

            # Import messages
            for msg_data in data.get("messages", []):
                message = MessageRecord(
                    conversation_id=conv.id,
                    role=msg_data["role"],
                    content=msg_data["content"],
                    tokens=msg_data.get("tokens", 0),
                    metadata_json=json.dumps(msg_data.get("metadata")) if msg_data.get("metadata") else None,
                )

                if "timestamp" in msg_data:
                    message.timestamp = datetime.fromisoformat(msg_data["timestamp"])

                session.add(message)

            session.commit()

            logger.info("Imported conversation for user: %s (id=%d)", conv.user_key, conv.id)

            session.close()
            return conv

        except Exception as exc:
            session.rollback()
            session.close()
            logger.error("Failed to import conversation: %s", exc, exc_info=True)
            raise ValueError(f"Failed to import conversation: {str(exc)}") from exc

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about stored conversations.

        Returns:
            Dictionary with conversation statistics
        """
        session = self.get_session()
        try:
            total_convs = session.query(ConversationRecord).count()
            total_messages = session.query(MessageRecord).count()

            if total_convs == 0:
                session.close()
                return {
                    "total_conversations": 0,
                    "total_messages": 0,
                    "total_tokens": 0,
                    "average_messages_per_conversation": 0,
                    "average_tokens_per_conversation": 0,
                }

            # Calculate aggregates
            convs = session.query(ConversationRecord).all()
            total_tokens = sum(conv.total_tokens for conv in convs)
            avg_messages = total_messages / total_convs if total_convs > 0 else 0
            avg_tokens = total_tokens / total_convs if total_convs > 0 else 0

            # Find longest conversation
            longest_conv = max(convs, key=lambda c: c.message_count, default=None)

            session.close()

            return {
                "total_conversations": total_convs,
                "total_messages": total_messages,
                "total_tokens": total_tokens,
                "average_messages_per_conversation": round(avg_messages, 2),
                "average_tokens_per_conversation": round(avg_tokens, 2),
                "longest_conversation_messages": longest_conv.message_count if longest_conv else 0,
                "longest_conversation_user": longest_conv.user_key if longest_conv else None,
            }

        except Exception as exc:
            session.rollback()
            session.close()
            logger.error("Failed to get conversation stats: %s", exc, exc_info=True)
            raise
