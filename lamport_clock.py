# lamport_clock.py
"""
Lamport Logical Clock implementation.
Provides mechanism for maintaining a logical clock in a distributed system.
"""


class LamportClock:
    def __init__(self, initial_value=0):
        """Initialize a new Lamport clock with the given initial value."""
        self.value = initial_value

    def tick(self):
        """Increment the clock before a local event or sending a message."""
        self.value += 1
        return self.value

    def update(self, received_clock_value):
        """
        Update the clock when receiving a message using the Lamport rule:
        clock = max(own_clock, received_clock) + 1
        """
        self.value = max(self.value, received_clock_value) + 1
        return self.value

    def get_time(self):
        """Get the current clock value."""
        return self.value