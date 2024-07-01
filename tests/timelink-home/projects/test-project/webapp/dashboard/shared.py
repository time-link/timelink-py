from pathlib import Path

from timelink.notebooks import TimelinkNotebook

project_home = Path(__file__).parent.parent.parent

tlnb = TimelinkNotebook(project_home=project_home)
tlnb.print_info()