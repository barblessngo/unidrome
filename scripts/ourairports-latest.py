import os
import shutil
import tempfile
import subprocess

class OurAirports:
    GIT_REPO = "https://github.com/davidmegginson/ourairports-data.git"

    @staticmethod
    def download_and_copy():
        with tempfile.TemporaryDirectory() as tmp_dir:
            print(f"Cloning repository into {tmp_dir}")
            try:
                subprocess.run(["git", "clone", "--depth", "1", OurAirports.GIT_REPO, tmp_dir], check=True)
                print("Repository successfully cloned.")
            except subprocess.CalledProcessError:
                print("Failed to clone repository.")
                return

            src_files = ['airports.csv', 'runways.csv']
            destination_dir = os.path.join('data', 'world', 'ourairports')
            if not os.path.exists(destination_dir):
                os.makedirs(destination_dir)
                print(f"Created directory {destination_dir}")

            for filename in src_files:
                src_path = os.path.join(tmp_dir, filename)
                dst_path = os.path.join(destination_dir, filename)
                if os.path.exists(src_path):
                    shutil.copy(src_path, dst_path)
                    print(f"Copied {filename} to {destination_dir}")
                else:
                    print(f"Warning: {filename} not found in the repository.")

if __name__ == "__main__":
    OurAirports.download_and_copy()

