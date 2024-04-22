""" Global utilities for the timelink package. """
import logging
from time import sleep
import requests
import docker


def is_docker_running():
    """Check if docker is running"""
    try:
        client = docker.from_env()
        client.ping()
        return True
    except docker.errors.DockerException as exec:
        logging.error(f"Could not connect to Docker. Is it running? {exec}")
        return False


def wait_container_start(client, container_id, timeout=15, stop_time=1, elapsed_time=0):
    """ waits for a docker container to start

    To be called after container.run()


    """
    # this necessary to get the status
    cont = client.containers.get(container_id)
    while cont.status not in ["running"] and elapsed_time < timeout:
        sleep(stop_time)
        cont = client.containers.get(container_id)
        elapsed_time += stop_time
    if cont.status != "running":
        raise RuntimeError("container did not start")


def get_container_by_name(name, start=True) -> docker.models.containers.Container:
    """Check if there is a fief container

    Args:

       """
    client = docker.from_env()
    for container in client.containers.list(filters={'name': name}):
        if container.status != "running" and start:
            container.start()
            wait_container_start(client, container.id)
        return container
    return None


def list_images(name=None, filters=None, all=False):
    """List images in the docker daemon

    Args:
        name: The name of the image
        filters: Filters to apply when listing images
        all: Show all images. Only images from a final layer (no children)
             are shown by default.

    See:
      :py:func:`docker.DockerClient.images.list`"""
    client = docker.from_env()
    return client.images.list(name=name, filters=filters, all=all)


def pull_image(image, tag=None, **kwargs):
    """Pull an image from a registry

    Args:
        image: The name of the image
        tag: The tag of the image
        kwargs: Additional arguments to pass to :py:func:`docker.DockerClient.images.pull`    """
    client = docker.from_env()
    return client.images.pull(image, tag=tag, **kwargs)


def get_docker_image_tags(image):
    url = f"https://registry.hub.docker.com/v2/repositories/{image}/tags/"
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception if the request failed
    data = response.json()
    tags = [(result['name'], result['last_updated'], result['digest']) for result in data['results']]
    return tags
