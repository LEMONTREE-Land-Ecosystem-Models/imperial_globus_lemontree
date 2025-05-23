"""This tool can be used to recursively download a directory from CEDA.

It uses requests.
"""

import requests
from pathlib import Path
from requests.auth import HTTPBasicAuth

from html.parser import HTMLParser


class LinkParser(HTMLParser):

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:

        if tag == "a":
            print(attrs)


def download_ceh_directory(
    ceh_path: str,
    out_dir: Path,
    user: str,
    passwd: str,
    exclude: tuple[str, ...] = (),
    dry_run: bool = False,
) -> bool:
    """Download the contents of a remote CEH directory.

    Args:
        ceh_path: The directory name within CEDA to be downloaded
        out_dir: A base path to download into
        user: A valid CEH user account name
        passwd: A valid CEH password
        exclude: A tuple of strings to match files to be excluded.
        dry_run: Prints out the expected file downloads and exclusions without
            downloading.
    """

    # Try and get the connection
    response = requests.get(ceh_path, auth=HTTPBasicAuth(user, passwd))
    if not response.ok:
        print(f"Could not connect to CEH: {str(response.reason)}")
        return False

    # Try and walk the directory from the base path - the directory stack is used to
    # keep a list of unvisited subdirectories within the basepath. When directories are
    # found they are added to the stack and the while loop continues until the stack is
    # exhausted.
    basepath = Path(ceda_path)
    current_working_path: list[str] = []
    directory_stack: list[list[str]] = []
    directory_stack_exhausted = False

    try:
        while not directory_stack_exhausted:

            # Loop over the entries in the current working path
            for fname, data in ftp_conn.mlsd(basepath.joinpath(*current_working_path)):

                # Handle different file types:
                # - Download type=file
                # - Add type=dir to stack
                # - Ignore type=cdir (.) and type=pdir (..) that are included in mlsd.
                if data["type"] == "file":

                    # Build the remote name and check if it is excluded
                    remote_file = str(basepath.joinpath(*current_working_path, fname))
                    if any([exc in remote_file for exc in exclude]):
                        print(f"Excluding: {remote_file}")
                        continue

                    # Otherwise create the local directory and get the local file name
                    local_dir = out_dir.joinpath(*current_working_path)
                    local_dir.mkdir(parents=True, exist_ok=True)
                    local_file = local_dir.joinpath(fname)

                    try:
                        if not dry_run:
                            with open(local_file, "wb") as fp:
                                ftp_conn.retrbinary(f"RETR {remote_file}", fp.write)
                        print(f"Downloaded: {remote_file}")
                    except ftplib.error_perm as err:
                        print(f"FTP error: {str(err)}")
                        return False

                if data["type"] == "dir":
                    directory_stack.append(current_working_path + [fname])

            if not directory_stack:
                directory_stack_exhausted = True
            else:
                current_working_path = directory_stack.pop(0)

    except ftplib.error_perm as err:
        print(f"FTP error: {str(err)}")
        return False

    return True


def download_ceda_directory_cli():
    r"""Download a CEDA directory via FTP.

    This command line tool takes a relative path within the CEDA data archive and
    recursively downloads the contents to a provided output directory. A CEDA username
    and FTP password are required - note that the FTP password is not the same as the
    CEDA login password and needs to be set up from your login page.

    Any files found in the directory that match strings supplied as `exclude` options
    will not be downloaded. Multiple exclude options can be provided.

    Example usage:

        python ceda_ftp_tool.py badc/cru/data/cru_ts/cru_ts_4.07 /tmp/4.06 \\
               user passwd -e station_counts -e 1901.2022 -e dat.gz
    """

    parser = argparse.ArgumentParser(
        description=textwrap.dedent(download_ceda_directory_cli.__doc__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("ceda_path", type=str, help="The CEDA base path")
    parser.add_argument("out_dir", type=str, help="An existing output directory")
    parser.add_argument("user", type=str, help="CEDA username")
    parser.add_argument("ftp_passwd", type=str, help="CEDA _FTP_ password")
    parser.add_argument(
        "-e",
        "--exclude",
        type=str,
        action="append",
        help="Exclude files matching these strings",
    )
    parser.add_argument(
        "--dry-run",
        help="Dry run showing files to be downloaded or excluded.",
        action="store_true",
    )

    args = parser.parse_args()

    # Argument validation
    out_dir = Path(args.out_dir)
    if not out_dir.exists():
        print(f"Output directory not found: {out_dir}")
        return 1

    # Print a short text report
    report_string = f"Downloading: {args.ceda_path}\nDestination: {args.out_dir}\n"
    if args.exclude:
        report_string += f"Excluding: {','.join(args.exclude)}\n"
    if args.dry_run:
        report_string += "DRY RUN: No files downloaded\n"

    print(report_string)

    success = download_ceda_directory(
        ceda_path=args.ceda_path,
        out_dir=out_dir,
        user=args.user,
        ftp_passwd=args.ftp_passwd,
        exclude=tuple(args.exclude),
        dry_run=args.dry_run,
    )

    return not success


if __name__ == "__main__":

    download_ceda_directory_cli()
