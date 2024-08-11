import datetime

from wikiteam3.dumpgenerator.config import Config

def log_error(config: Config, to_stdout=False , text="") -> None:
    """Log error in errors.log"""
    if text:
        with open(f"{config.path}/errors.log", "a", encoding="utf-8") as outfile:
            output = "{}: {}\n".format(
                datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                text,
            )
            outfile.write(output)
    if to_stdout:
        print(text)
