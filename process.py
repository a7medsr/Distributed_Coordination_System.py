import logging
import threading
import time
import random
from queue import Queue, Empty
from lamport_clock import LamportClock

class Process(threading.Thread):
    def __init__(self, process_id, num_processes):
        """Initialize a process with its ID and references to other processes."""
        super().__init__(name=f"Process-{process_id}")
        self.process_id = process_id
        self.num_processes = num_processes
        self.clock = LamportClock()
        self.message_queue = Queue()
        self.active = True
        self.is_leader = False
        self.current_leader = None
        self.processes = {}  # Will be populated with references to other processes
        self.heartbeat_timeout = 3  # Seconds before assuming leader is down
        self.last_heartbeat = time.time()

        # Create a process-specific logger
        self.logger = logging.getLogger(f"process-{process_id}")
        # No need to set formatter here as main.py will handle that

    def set_processes(self, processes):
        """Set references to all processes in the system."""
        self.processes = processes

    def run(self):
        """Main process execution loop."""
        while self.active:
            try:
                # Generate some local events
                if random.random() < 0.2:  # 20% chance of local event
                    self._local_event()

                # Send messages to random processes
                if random.random() < 0.3:  # 30% chance of sending a message
                    self._send_random_message()

                # If I am the leader, send heartbeat messages
                if self.is_leader:
                    self._send_heartbeat()

                # Check for leader failure if I'm not the leader
                elif self.current_leader is not None:
                    if time.time() - self.last_heartbeat > self.heartbeat_timeout:
                        self._detect_leader_failure()

                # Process incoming messages
                try:
                    message = self.message_queue.get(block=False)
                    self._handle_message(message)
                    self.message_queue.task_done()
                except Empty:
                    pass

                # Small sleep to prevent CPU hogging
                time.sleep(0.1)

            except Exception as e:
                self._log(f"Error in process loop: {e}", level=logging.ERROR)

    def _local_event(self):
        """Perform a local event and update the clock."""
        self.clock.tick()
        self._log("Local event occurred")

    def _send_random_message(self):
        """Send a message to a random process."""
        if len(self.processes) <= 1:
            return

        recipient_id = random.choice([pid for pid in self.processes.keys()
                                      if pid != self.process_id])
        self._send_message(recipient_id, "REGULAR", {"content": f"Hello from {self.process_id}"})

    def _send_message(self, recipient_id, msg_type, payload=None):
        """Send a message to another process."""
        if recipient_id not in self.processes or not self.processes[recipient_id].active:
            return

        # Increment clock before sending
        self.clock.tick()
        current_time = self.clock.get_time()

        message = {
            "sender_id": self.process_id,
            "clock": current_time,
            "type": msg_type,
            "payload": payload or {}
        }

        # Simulate network delay
        delay = random.uniform(0.1, 0.5)
        threading.Timer(delay, self._deliver_message, args=[recipient_id, message]).start()

        self._log(f"Sending {msg_type} message to Process {recipient_id}")

    def _deliver_message(self, recipient_id, message):
        """Deliver a message to the recipient's queue (after network delay)."""
        if recipient_id in self.processes and self.processes[recipient_id].active:
            self.processes[recipient_id].message_queue.put(message)

    def _handle_message(self, message):
        """Process an incoming message."""
        sender_id = message["sender_id"]
        sender_clock = message["clock"]
        msg_type = message["type"]

        # Update clock based on received message
        self.clock.update(sender_clock)

        if msg_type == "REGULAR":
            self._log(f"Received message from Process {sender_id}")

        elif msg_type == "HEARTBEAT":
            self.last_heartbeat = time.time()
            self.current_leader = sender_id

        elif msg_type == "ELECTION":
            # Respond to election message (Bully algorithm)
            self._log(f"Received election message from Process {sender_id}")
            self._send_message(sender_id, "ELECTION_REPLY")

            # Start an election myself (only if not already in one)
            if random.random() < 0.3:  # Avoid all processes starting elections at once
                self._start_election()

        elif msg_type == "ELECTION_REPLY":
            self._log(f"Received election reply from Process {sender_id}")
            # If we get a reply, we know we're not the leader
            self.is_leader = False

        elif msg_type == "LEADER_ANNOUNCEMENT":
            new_leader = message["payload"]["leader_id"]
            self._log(f"Process {new_leader} has been elected as leader")
            self.current_leader = new_leader
            self.is_leader = (new_leader == self.process_id)
            self.last_heartbeat = time.time()

    def _detect_leader_failure(self):
        """Detect if the current leader has failed and start an election."""
        if self.current_leader is not None:
            self._log(f"Detected leader {self.current_leader} failure! Starting election...")
            self._start_election()

    def _start_election(self):
        """Start a new leader election (Bully Algorithm)."""
        # Send election messages to all processes with higher IDs
        higher_processes = [pid for pid in self.processes.keys()
                            if pid > self.process_id and self.processes[pid].active]

        if not higher_processes:
            # No higher processes, I become the leader
            self._declare_leader()
        else:
            # Send election messages to higher processes
            for pid in higher_processes:
                self._send_message(pid, "ELECTION")

            # Wait for replies, if none, become leader
            # This is simulated with a timer
            election_timeout = random.uniform(1.0, 2.0)  # Different timeouts to avoid conflicts
            threading.Timer(election_timeout, self._check_election_result).start()

    def _check_election_result(self):
        """Check if we should become leader after timeout."""
        # If we're still active and not already a leader or have another leader, become one
        if self.active and not self.is_leader and self.current_leader is None:
            higher_active_process = any(pid > self.process_id and self.processes[pid].active
                                        for pid in self.processes.keys())
            if not higher_active_process:
                self._declare_leader()

    def _declare_leader(self):
        """Declare this process as the leader."""
        self.is_leader = True
        self.current_leader = self.process_id

        # Announce leadership to all processes
        for pid in self.processes.keys():
            if pid != self.process_id and self.processes[pid].active:
                self._send_message(pid, "LEADER_ANNOUNCEMENT", {"leader_id": self.process_id})

        self._log("Declares itself new leader")

    def _send_heartbeat(self):
        """Send heartbeat messages to all processes if I am the leader."""
        if not self.is_leader:
            return

        for pid in self.processes.keys():
            if pid != self.process_id and self.processes[pid].active:
                self._send_message(pid, "HEARTBEAT")

    def kill(self):
        """Simulate process failure."""
        self._log("Process is shutting down")
        self.active = False

    def _log(self, message, level=logging.INFO):
        """Log a message with process ID and clock value."""
        extra = {
            'process_id': self.process_id,
            'clock': self.clock.get_time()
        }

        if level == logging.INFO:
            self.logger.info(message, extra=extra)
        elif level == logging.WARNING:
            self.logger.warning(message, extra=extra)
        elif level == logging.ERROR:
            self.logger.error(message, extra=extra)
        elif level == logging.DEBUG:
            self.logger.debug(message, extra=extra)
        elif level == logging.CRITICAL:
            self.logger.critical(message, extra=extra)