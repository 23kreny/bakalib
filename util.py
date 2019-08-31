from pathlib import Path

conf_dir = Path.home().joinpath(".bakalaris")
token_file_path = conf_dir.joinpath("token.txt")
domain_file_path = conf_dir.joinpath("domain.txt")
schooldb_file_path = conf_dir.joinpath("schooldb.json")
