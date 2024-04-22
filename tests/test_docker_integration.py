import subprocess
import time
from timelink.global_utilities import (
    is_docker_running, list_images, pull_image,
    wait_container_start,
    get_container_by_name,
    get_docker_image_tags)


def test_is_docker_running():
    try:
        subprocess.check_output(["docker", "info"])
        assert is_docker_running() is True
    except subprocess.CalledProcessError:
        assert is_docker_running() is False


def test_pull_image():
    img = pull_image("ghcr.io/fief-dev/fief")
    assert img is not None


def test_list_images():
    images = list_images("ghcr.io/fief-dev/fief")
    assert images is not None
    print()
    for img in images:
        print(img.id[8:16], img.tags)


def test_get_docker_image_tags(name="timelinkserver/kleio-server"):
    tags = get_docker_image_tags(name)
    assert tags is not None
    print()
    for tag in tags:
        print(tag)


def test_get_container_by_name():
    container = get_container_by_name("fief-server")
    assert container is not None
    print(container.id)
    print(container.status)
    print(container.name)
    print(container.image.tags)
    print(container.attrs)
    print(container.logs())
    print(container.top())
    print(container.stats())


def test_wait_container_start():
    container = get_container_by_name("fief-server")
    container.stop()
    time.sleep(1)
    wait_container_start(container.client, container.id)
    assert container.status == "running"
    print(container.status)
