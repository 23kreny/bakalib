from pathlib import Path

conf_dir = Path.home().joinpath(".bakalaris")
auth_file = conf_dir.joinpath("auth.json")

if not conf_dir.is_dir():
    conf_dir.mkdir()
