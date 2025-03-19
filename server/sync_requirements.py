# flake8: noqa
import re
from pathlib import Path

import pkg_resources


def update_requirements_in(requirements_in_path: str, requirements_txt_path: str):
    """
    Update requirements.in with exact versions from requirements.txt

    Args:
        requirements_in_path: Path to requirements.in file
        requirements_txt_path: Path to requirements.txt file
    """
    # Read requirements.txt and parse versions
    txt_versions = {}
    with open(requirements_txt_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                # Parse package name and version
                try:
                    req = pkg_resources.Requirement.parse(line)
                    package_name = req.project_name
                    # Get exact version without any specifiers
                    version = re.search(r"==([^\s;]+)", line)
                    if version:
                        txt_versions[package_name.lower()] = version.group(1)
                except:
                    continue

    # Read and update requirements.in
    updated_lines = []
    with open(requirements_in_path) as f:
        for line in f:
            original_line = line.strip()
            if original_line and not original_line.startswith("#"):
                try:
                    req = pkg_resources.Requirement.parse(original_line)
                    package_name = req.project_name.lower()
                    if package_name in txt_versions:
                        # Replace or add version specification
                        if "==" in original_line:
                            updated_line = re.sub(
                                r"==[\d\.]+",
                                f"=={txt_versions[package_name]}",
                                original_line,
                            )
                        else:
                            updated_line = (
                                f"{package_name}=={txt_versions[package_name]}"
                            )
                        updated_lines.append(updated_line)
                        continue
                except:
                    pass
            updated_lines.append(original_line)

    # Write updated requirements.in
    with open(requirements_in_path, "w") as f:
        f.write("\n".join(updated_lines) + "\n")


if __name__ == "__main__":
    update_requirements_in("requirements.in", "requirements.txt")
