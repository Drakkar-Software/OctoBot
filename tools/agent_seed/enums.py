#  Demo-only agent seed enums.

import enum


class BootstrapScenario(str, enum.Enum):
    # Start the grid automation on Seed kraken A (default).
    GRID = "grid"
    # Start the index automation on Seed kraken B.
    INDEX = "index"
    # Create an index automation on Seed kraken B, then stop it: completed state in the UI.
    COMPLETED = "completed"
    # Stop and restart the grid automation, then check it keeps its name.
    LIFECYCLE = "lifecycle"
    # Every scenario above, in that order.
    ALL = "all"
