"""Console script for timelink."""
import sys
import click


@click.command()
def main(args=None):
    """Console script for timelink."""
    click.echo("Replace this message by putting your code into "
               "timelink.cli.main")
    click.echo("See click documentation at https://click.palletsprojects.com/")
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
