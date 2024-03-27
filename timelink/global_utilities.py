""" Global utilities for the timelink package. """
# Utilities

import logging
import docker


def is_docker_running():
    """Check if docker is running"""
    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception as exec:
        logging.error(f"Could not connect to Docker. Is it running? {exec}")
        return False
