import argparse
import subprocess
import os
import sys

TIMELINK_APP_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_APP_SCRIPT = os.path.join(TIMELINK_APP_DIR, 'web\\timelink_web.py')

def run_script(script_path, *args, blocking=True, env=None, **kwargs):
    """Helper function to run a Python script. The script is blocking unless background is set to True."""
    
    command = [sys.executable, script_path] + list(args)

    try:
        process = subprocess.Popen(command, **kwargs, env=env)
        if blocking:
            process.wait()
        return process
    except Exception as e:
        print(f"Failed to run {script_path}: {e}")
        return None



def launch_command(args):
    """Handles the 'launch' command."""
    
    db_type = args.subcommand or 'both'
    env = os.environ.copy()
    env['DB_TYPE'] = db_type

    process = run_script(WEB_APP_SCRIPT, *args.extra_args, env=env)
    
    if process:
        print("Launching the Timelink Web Interface...")
        try:
            process.wait()
            sys.exit(0)
        except KeyboardInterrupt:
            process.terminate()
            process.wait()
            print("The Timelink Web App was successfully closed.")
            sys.exit(0) # Stop launcher execution
    else:
        print("Timelink Web App: Failed to launch.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Timelink Web App CLI launcher.",
        formatter_class=argparse.RawTextHelpFormatter # For better multiline help
    )

    # Add a version argument
    parser.add_argument(
        '-v', '--version', action='version', version='Timelink Web App version 0.1.0',
        help="Show Timelink Web App version."
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # --- 'launch' command subparser ---
    launch_parser = subparsers.add_parser(
        'launch',
        help='launch web app',
        description='''\
                Launches the Timelink Web Interface with passed arguments as options.
        ''',
        add_help=True
    )

    launch_parser.add_argument('subcommand', choices=['sqlite', 'postgres', 'both'], nargs='?', default='sqlite',
            help='Database type to use (db, pd, both). Default is both.'
    )

    # Capture all remaining arguments for passing to the sub-script
    launch_parser.add_argument('extra_args', nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    # Parse arguments
    args = parser.parse_args()

    # Handle the command based on 'dest' attribute
    if args.command == 'launch':
        launch_command(args)
    elif args.command is None:
        # If no command is provided (e.g., just 'timelink')
        parser.print_help()
    else:
        # This part should ideally not be reached if subparsers are defined correctly.
        print(f"Error: Unknown command '{args.command}'")
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()