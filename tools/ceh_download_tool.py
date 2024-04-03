"""This tool can be used to recursively download a directory from CEDA.

It uses requests.
"""

import argparse
from html.parser import HTMLParser
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth
import textwrap


def download_ceh_directory(
    ceh_path: str,
    out_dir: Path,
    user: str,
    passwd: str,
    dry_run: bool = False,
) -> bool:
    """Download the contents of a remote CEH directory.

    Args:
        ceh_path: The directory name within CEDA to be downloaded
        out_dir: A base path to download into
        user: A valid CEH user account name
        passwd: A valid CEH password
        dry_run: Prints out the expected file downloads and exclusions without
            downloading.
    """

    # Try and get an authenticated response from the path
    response = requests.get(ceh_path, auth=HTTPBasicAuth(user, passwd))
    if not response.ok:
        print(f"Could not connect to CEH: {str(response.reason)}")
        return False

    # Define a link parser that will populate a list of files.
    link_list = []

    class LinkParser(HTMLParser):

        def handle_starttag(
            self, tag: str, attrs: list[tuple[str, str | None]]
        ) -> None:

            if tag == "a":
                attrs_dict = dict(attrs)
                if "href" in attrs_dict:
                    link_list.append(attrs_dict["href"])

    parser = LinkParser()
    parser.feed(response.text)

    # Now download them all
    for file in link_list:

        print(f"Downloading: {file}")

        if not dry_run:
            response = requests.get(ceh_path + file)

            if response.ok:
                with open(out_dir.joinpath(file), "wb") as outf:
                    outf.write(response.content)
            else:
                print(f"Could not download: {str(response.reason)}")
                return False

    return True


def download_ceh_directory_cli():
    r"""Download a CEH directory via HTTP.

    This command line tool takes the URL of a CEH data archive and downloads the
    contents to a provided output directory. A CEH username and  password are required.

    Example usage:

        python ceh_download_tool.py \\
            https://catalogue.ceh.ac.uk/datastore/eidchub/31dd5dd3-85b7-45f3-96a3-6e6023b0ad61/extracted/ \\
            /tmp/4.06 user passwd
    """

    parser = argparse.ArgumentParser(
        description=textwrap.dedent(download_ceh_directory.__doc__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("ceh_path", type=str, help="The CEH base path")
    parser.add_argument("out_dir", type=str, help="An existing output directory")
    parser.add_argument("user", type=str, help="CEH username")
    parser.add_argument("passwd", type=str, help="CEH password")
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
    report_string = f"Downloading: {args.ceh_path}\nDestination: {args.out_dir}\n"
    if args.dry_run:
        report_string += "DRY RUN: No files downloaded\n"

    print(report_string)

    success = download_ceh_directory(
        ceh_path=args.ceh_path,
        out_dir=out_dir,
        user=args.user,
        passwd=args.passwd,
        dry_run=args.dry_run,
    )

    return not success


if __name__ == "__main__":

    download_ceh_directory_cli()
