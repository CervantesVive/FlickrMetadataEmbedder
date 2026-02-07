"""Track processed photos for resumability.

State file is a JSON dict: {photo_id: unix_timestamp, ...}
Batch-saves every 50 photos to reduce I/O overhead.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_STATE_FILENAME = ".flickr_embed_state.json"
_BATCH_SIZE = 50


class StateManager:
    """Tracks processed photos for --resume support.

    Saves state to a JSON file in the output directory.
    Batch-writes every _BATCH_SIZE photos to minimize disk I/O.
    """

    def __init__(self, state_dir: str | Path) -> None:
        self._state_path = Path(state_dir) / _STATE_FILENAME
        self._state: dict[str, float] = {}
        self._dirty_count = 0

    def load(self) -> set[str]:
        """Load state from disk.

        Returns:
            Set of already-processed photo_ids.
        """
        if self._state_path.exists():
            try:
                with open(self._state_path, "r") as f:
                    self._state = json.load(f)
                logger.info("Loaded state: %d already processed", len(self._state))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load state file: %s", e)
                self._state = {}
        return set(self._state.keys())

    def mark_processed(self, photo_id: str) -> None:
        """Mark a photo as processed. Batch-saves to disk."""
        self._state[photo_id] = time.time()
        self._dirty_count += 1
        if self._dirty_count >= _BATCH_SIZE:
            self.save()

    def save(self) -> None:
        """Flush pending state to disk."""
        if self._dirty_count > 0:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._state_path, "w") as f:
                json.dump(self._state, f)
            self._dirty_count = 0

    @property
    def processed_count(self) -> int:
        """Number of photos tracked in state."""
        return len(self._state)


def load_state(state_dir: str | Path) -> set[str]:
    """Convenience function to load state without keeping a StateManager."""
    mgr = StateManager(state_dir)
    return mgr.load()
