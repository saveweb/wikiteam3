import os
import subprocess
DUMPER_MARK = '<!-- DUMPER -->'
UPLOADER_MARK = '<!-- UPLOADER -->'

if __name__ == "__main__":
    with open("README.md") as f:
        readme = f.read()
    dumper_help = subprocess.run(["wikiteam3dumpgenerator", "-h"], capture_output=True, text=True)
    uploader_help = subprocess.run(["wikiteam3uploader", "-h"], capture_output=True, text=True)
    assert dumper_help.returncode == 0 and uploader_help.returncode == 0
    dumper_help = dumper_help.stdout
    uploader_help = uploader_help.stdout

    readme = readme.split(DUMPER_MARK)
    assert len(readme) == 3
    readme[1] = f"\n<details>\n\n```bash\n{dumper_help}\n```\n</details>\n\n"
    readme = DUMPER_MARK.join(readme)

    readme = readme.split(UPLOADER_MARK)
    assert len(readme) == 3
    readme[1] = f"\n<details>\n\n```bash\n{uploader_help}\n```\n</details>\n\n"
    readme = UPLOADER_MARK.join(readme)

    with open("README.md", "w") as f:
        f.write(readme)