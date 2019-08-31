from pathlib import Path

conf_dir = Path.home().joinpath(".bakalaris")
auth_file_path = conf_dir.joinpath("auth.json")
schooldb_file_path = conf_dir.joinpath("schooldb.json")

if not conf_dir.is_dir():
    conf_dir.mkdir()
