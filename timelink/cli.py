"""Console script for timelink."""
import sys
import click


@click.group()
def cli():
    pass


@click.command()
def mhk():
    """MHK mode in Timelink-py"""
    mhk.echo("MHK cli in timelink-py")
    return 0


@click.command()
def timelink():
    """timelink command line interface"""
    timelink.echo("timelink cli")
    return 0


cli.add_command(mhk)
cli.add_command(timelink)


if __name__ == "__main__":
    cli()  # pragma: no cover
