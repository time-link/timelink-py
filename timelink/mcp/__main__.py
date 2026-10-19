"""Run the Timelink MCP server over stdio: ``python -m timelink.mcp``."""

from timelink.mcp.server import mcp


def main() -> None:
    """Console-script entry point (``timelink-mcp``)."""
    mcp.run()


if __name__ == "__main__":
    main()
