from pathlib import Path
import subprocess

# Which variables to download - file names structures are not consistent
variables = (
    ("pr", "pr/CHELSA_pr_{month:02d}_{year}_V.2.1.tif"),
    ("clt", "clt/CHELSA_clt_{month:02d}_{year}_V.2.1.tif"),
    # ("tas", "tas/CHELSA_tas_{month:02d}_{year}_V.2.1.tif"),
    # ("vpd", "vpd/CHELSA_vpd_{month:02d}_{year}_V.2.1.tif"),
    # ("rsds", "rsds/CHELSA_rsds_{year}_{month:02d}_V.2.1.tif"),  # FFS, why!
)


for var, file_format in variables:
    # Generate a file containing all the required download paths - it is more efficient
    # to allow wget to handle a collection of files using the same connection that to
    # download each one on a new connection.
    file_paths = [
        "https://os.zhdk.cloud.switch.ch/chelsav2/GLOBAL/monthly/"
        + file_format.format(year=year, month=month)
        + "\n"
        for year in range(1979, 2019)
        for month in range(1, 13)
    ]

    input_files = Path("input_files.txt")
    with open(input_files, "w") as f:
        f.writelines(file_paths)

    # Create the output path and run the wget command
    Path(var).mkdir(exist_ok=True)
    subprocess.run(["wget", "-P", var, "--input-file=input_files.txt"])

    # Remove download file list
    input_files.unlink()
