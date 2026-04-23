import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

# Load data and calculate total request and processing times
data = pd.read_csv(
    "request_times.csv",
    parse_dates=["created_at", "started_at", "finished_at"],
)
data["runtime_minutes"] = (
    (data["finished_at"] - data["created_at"])
    .to_numpy()
    .astype("timedelta64[m]")
    .astype("int")
)
data["processing_seconds"] = (
    (data["finished_at"] - data["started_at"])
    .to_numpy()
    .astype("timedelta64[s]")
    .astype("int")
)

# Plot runtime and processing time as a function of submission time
fig, (ax1, ax2) = plt.subplots(nrows=2, sharex=True)


ax1.scatter(data["created_at"], data["runtime_minutes"])
ax1.set_ylabel("Request run time (minutes)")


ax2.scatter(data["created_at"], data["processing_seconds"])
ax2.set_ylabel("Request processing time (seconds)")

# Shared time axis
ax2.set_xlabel("Submission time")
time_axis_format = DateFormatter("%H:%m")
ax2.xaxis.set_major_formatter(time_axis_format)

plt.tight_layout()
plt.show()
