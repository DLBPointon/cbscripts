def connect_to_db():
    """
    Connects to the database and query for Comics where
    the current path does not match the proposed path.
    """


def move_that_thang():
    """
    Moves the comic book file to the proposed path.
    """


def update_db():
    """
    Once successfully moved, updates the database fields so that
    the current path matches the proposed path.
    """


def main(
    context, input_path, dry_run=False, subdirectory_search=False, output_directory=None
):
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

    connect_to_db()

    move_that_thang()

    update_db()  # that current_path = proposed_path
