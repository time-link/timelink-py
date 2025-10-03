import subprocess
import os
import pysolr
import json


class SolrWrapper:

    """
    A wrapper for the Solr client with configuration options.

    Args:
            solr_container_name: Name of the container for the solr instance.
            solr_port: Port where the solr container should run
            solr_core_name: Name of the core for the instance of solr that is going to run
            solr_version: Version of solr container to install. Defaults to slim installation
            solr_settings_dir: location where solr settings will be saved (defaults to where the app is initiated from)
            always_commit: signals to the Solr object to either commit or not commit by default for any solr request
            timeout: default time until a connection drops

        Returns:
            A TimelinkWebApp instance
    """

    def __init__(
        self,
        solr_settings_dir: str,
        solr_container_name: str = "timelink_solr",
        solr_port: str = "8983",
        solr_core_name: str = "timelink_core",
        solr_version: str = "slim",
        always_commit=True,
        timeout=30
    ):

        self.solr_container_name = solr_container_name
        self.solr_port = solr_port
        self.solr_core_name = solr_core_name
        self.solr_settings_dir = f"{os.getcwd()}/solrdata:/var/solr" if not solr_settings_dir else solr_settings_dir
        self.always_commit = always_commit
        self.timeout = timeout
        self.solr_version = solr_version

        self.solr_client = None

    def setup_solr_container(self):
        """Startup the solr container."""

        print("Checking for Solr container...")

        # Check if container is already running.
        container_running_check = subprocess.run(
            ["docker", "ps", "-f", f"name={self.solr_container_name}", "--format", "{{.Names}}"],
            capture_output=True, text=True
        )
        if self.solr_container_name in container_running_check.stdout:
            print(f"Solr container '{self.solr_container_name}' is already running.")
        else:
            # Container exists but is stopped.
            container_exists_check = subprocess.run(
                ["docker", "ps", "-a", "-f", f"name={self.solr_container_name}", "--format", "{{.Names}}"],
                capture_output=True, text=True
            )
            if self.solr_container_name in container_exists_check.stdout:
                # Container exists
                print(f"Starting existing Solr container '{self.solr_container_name}'...")
                subprocess.run(["docker", "start", self.solr_container_name], check=True)
            else:
                # Container does not exist
                print(f"Creating and starting new Solr container '{self.solr_container_name}' with core '{self.solr_core_name}' ...")
                subprocess.run([
                    "docker", "run", "-d",
                    "-v", self.solr_settings_dir,
                    "-p", "8983:8983",
                    "--name", self.solr_container_name,
                    f"solr:{self.solr_version}",
                    "solr-precreate", self.solr_core_name
                ], check=True)

    def init_solr_client(self):
        """Initiate a solr client instance."""

        solr_url = f'http://localhost:{self.solr_port}/solr/{self.solr_core_name}'

        self.solr_client = pysolr.Solr(solr_url, always_commit=self.always_commit, timeout=self.timeout)

    def health_check(self):
        """Pings the container to check for health status."""

        ping = self.solr_client.ping()
        resp = json.loads(ping)

        if resp.get('status') == 'OK':
            print('Solr OK!')
