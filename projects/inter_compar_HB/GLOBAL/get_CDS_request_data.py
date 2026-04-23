from ecmwf.datastores import Client
import pandas as pd


# Load the client instance - requires credentials file
client = Client()
client.check_authentication()

# Retrieve job IDs
jobs = client.get_jobs(sortby="-created", status="successful")

# Loop over paged sets of request ids
request_ids = []
while jobs is not None:
    request_ids.extend(jobs.request_ids)
    jobs = jobs.next

# Use request IDs to retrieve Request objects with runtime data
# Would need second request to get Results to get file size as:
# client.get_results(request_id).content_length

requests = []

for request_id in request_ids:
    request = client.get_remote(request_id)

    requests.append(
        dict(
            id=request_id,
            created_at=request.created_at,
            started_at=request.started_at,
            finished_at=request.finished_at,
        )
    )


df = pd.DataFrame.from_records(requests)
df.to_csv("request_times.csv")
