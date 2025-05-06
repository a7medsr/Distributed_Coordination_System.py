# main.py
"""
Main runner for the distributed coordination system simulation.
Creates processes, initiates the simulation, and handles the failure scenario.
"""

import logging
import time
import random
import threading
from process import Process


def setup_logging():
    """Set up logging configuration for both main and process loggers."""
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create formatters
    process_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] Process %(process_id)s | Clock %(clock)s | %(message)s',
        datefmt='%H:%M:%S'
    )

    main_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] MAIN | %(message)s',
        datefmt='%H:%M:%S'
    )

    # Custom filter to select the right formatter based on logger name
    class FormatFilter(logging.Filter):
        def filter(self, record):
            if record.name.startswith('process-'):
                console_handler.setFormatter(process_formatter)
            else:
                console_handler.setFormatter(main_formatter)
            return True

    # Add filter to handler
    console_handler.addFilter(FormatFilter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)


def main():
    # Set up logging
    setup_logging()
    logger = logging.getLogger("main")

    # Create processes
    num_processes = 5
    processes = {}

    logger.info(f"Creating {num_processes} processes...")
    for i in range(1, num_processes + 1):
        processes[i] = Process(i, num_processes)

    # Share process references
    for process in processes.values():
        process.set_processes(processes)

    # Start all processes
    logger.info("Starting all processes...")
    for process in processes.values():
        process.start()

    # Let the highest ID process become the initial leader
    initial_leader_id = max(processes.keys())
    time.sleep(2)  # Give processes time to start up
    logger.info(f"Initiating leader election with Process {initial_leader_id} as expected leader...")
    processes[initial_leader_id]._start_election()

    # Let the system run for some time
    time.sleep(10)

    # Kill the leader to simulate failure
    leader_id = max(p_id for p_id, p in processes.items() if p.active)
    logger.info(f"Killing leader (Process {leader_id})...")
    processes[leader_id].kill()

    # Wait for re-election to occur
    time.sleep(5)

    # Check the new leader
    active_processes = [p for p in processes.values() if p.active]
    leaders = [p for p in active_processes if p.is_leader]

    if leaders:
        logger.info(f"New leader is Process {leaders[0].process_id}")
    else:
        logger.info("No leader elected!")

    # Let the system run a bit longer
    time.sleep(5)

    # Shutdown all processes
    logger.info("Shutting down all processes...")
    for process in active_processes:
        process.kill()

    # Wait for threads to finish
    for process in processes.values():
        process.join(timeout=1.0)

    logger.info("Simulation completed.")


if __name__ == "__main__":
    main()