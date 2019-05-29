from pathlib import Path

conf_dir = Path.home().joinpath(".org.kreny.bakalib")
auth_file_path = conf_dir.joinpath("auth.json")
auth_file = str(auth_file_path)
