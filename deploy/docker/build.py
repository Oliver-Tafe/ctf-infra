#!/usr/bin/env python3

import argparse
import os
import subprocess
import yaml

import ctftool


def main():
    retval = 0
    parser = argparse.ArgumentParser()
    parser.add_argument("--push", action="store_true")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="increase verbosity"
    )
    args, _ = parser.parse_known_args()

    with open("deploy.sh", "w") as deploy_script:
        try:
            for challenge in ctftool.Challenge.load_all():
                if challenge.deploy and challenge.deploy.docker:
                    print(f"Building from {challenge.path}...")
                    image_name = f"challenge-{challenge.name}"
                    if (image_prefix := os.environ.get("IMAGE_PREFIX")):
                        image_name = f"{image_prefix}-{image_name}"
                    if (image_repo := os.environ.get("IMAGE_REPO")):
                        image_name = f"{image_repo}/{image_name}"
                        subprocess.run(["docker", "pull", f"{image_name}:latest"])
                    if args.verbose:
                        subprocess.run(["docker", "build", "-t", f"{image_name}:{challenge.githash}", "."], cwd=os.path.dirname(challenge.path), check=True)
                        subprocess.run(["docker", "tag", f"{image_name}:{challenge.githash}", f"{image_name}:latest"], check=True)
                    else:
                        subprocess.run(["docker", "build", "-t", f"{image_name}:{challenge.githash}", "."], stdout=subprocess.DEVNULL, cwd=os.path.dirname(challenge.path), check=True)
                        subprocess.run(["docker", "tag", f"{image_name}:{challenge.githash}", f"{image_name}:latest"], stdout=subprocess.DEVNULL, check=True)
                    if args.push:
                        subprocess.run(["docker", "push", f"{image_name}:{challenge.githash}"], check=True)
                        subprocess.run(["docker", "push", f"{image_name}:latest"], check=True)

                    ports = []
                    for port in challenge.deploy.ports:
                        ports.append(f"-p {port.external}:{port.internal}/{port.protocol}")

                    deploy_script.write(f"docker run -d {' '.join(ports)} -t {image_name}\n")
        except subprocess.CalledProcessError as e:
            retval = -1
    subprocess.run(["chmod", "+x", "deploy.sh"])
    return retval

if __name__ == "__main__":
    main()
