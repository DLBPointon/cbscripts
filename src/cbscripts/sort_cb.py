from pathlib import Path
from cbscripts.utils import get_comic_files

def main(context, input_path, dry_run=False, subdirectory_search=False, output_directory=None):
    """
    Main function for the SORT subcommand.

    Args:
        input_path (str): The path to the directory containing comic book files.
        subdirectory_search (bool, optional): Whether to search for comic book files in all subdirectories. Defaults to False.

    Returns:
        None

    Outputs:
        if dry_run: a file of comics, details and where to send them in JSON format
        else moves files into new directory structure
    """

    path = Path(input_path)
    comic_files = get_comic_files(path, subdirectory_search)
