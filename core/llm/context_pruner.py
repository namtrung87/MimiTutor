class ContextPruner:
    """
    Utility to prune and compact message history and text blocks for LLM context limits.
    """
    @staticmethod
    def prune_text(text: str, max_tokens: int = 15000) -> str:
        """Heuristic-based text pruning."""
        # Heuristic: 1 token ~ 4 characters
        max_chars = max_tokens * 4
        if len(text) > max_chars:
            half = max_chars // 2
            return text[:half] + "\n... [CONTENT PRUNED] ...\n" + text[-half:]
        return text

    @staticmethod
    def compact_context(messages: list) -> list:
        """Keep essential messages if context is too long and handle format normalization."""
        if not messages or not isinstance(messages, list) or len(messages) <= 12:
            return messages
            
        # Keep first 2 (system/context) and last 10
        compacted = list(messages[:2]) + list(messages[-10:])
        return compacted
