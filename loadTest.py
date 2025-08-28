import sys
import requests
import time
import shutil
from datetime import timedelta

if len(sys.argv) < 2:
    raise SystemExit("Error: No argument provided.")

base_url = sys.argv[1]
print("Starting load test on: ", base_url)

try:
    response = requests.post(
        f"{base_url}user/login", 
        json={
            "uuid": "281d10f6-3bed-40c2-96f0-ba120f38ecbd",
            "passkey": "secret"
        }
    )
    response.raise_for_status()
    print("Status code:", response.status_code)
    print("Response:", f"{response.text[:100]}...")
    token = response.json().get("token")
except Exception as e:
    print("Request failed (/user/login):", e)
    raise SystemExit("Error: Couldn't login")

start_time = time.time()

for job in range(5):
    print ("\nStarting Job:", job)
    
    try:
        with open("stress_resume.pdf", "rb") as file:
            response = requests.post(
                f"{base_url}index_resume/upload", 
                headers = {"Authorization": f"Bearer {token}"},
                files = {"file": file}
            )
            print("Status code:", response.status_code)
            print("Response:", response.text)
            uuid = response.json().get("uuid")
    except Exception as e:
        print("Request failed (/index_resume/upload):", e)
        raise SystemExit("Error: Indexing resume")

    while True:
        try:
            response = requests.get(
                f"{base_url}index_resume/status/{uuid}"
            )
            print(f"\r{" " * shutil.get_terminal_size().columns}\rStatus code: {response.status_code} Response: {response.text} Elapsed: {timedelta(seconds=int(time.time() - start_time))}", end="")
            if response.json().get("status") == "Completed!" or response.status_code != 200:
                print()
                break
        except Exception as e:
            print("Request failed (/index_resume/status):", e)
            raise SystemExit("Error: Getting status")
        time.sleep(1)

    print("Finished Job:", job)