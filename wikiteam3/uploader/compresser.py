
import os
from pathlib import Path
import subprocess
import time
from typing import Tuple, Union
import warnings


class ZstdCompressor:
    DEFAULT_LEVEL = 17
    MIN_VERSION = (1, 4, 8)
    bin_zstd = "zstd"

    def __init__(self, bin_zstd: str = "zstd"):
        """ versionCheck: check if zstd version is >= 1.4.8 """
        self.bin_zstd = bin_zstd
        version = self.versionNumber()
        assert version >= self.MIN_VERSION, f"zstd version must be >= {self.MIN_VERSION}"
        # if v1.5.0-v1.5.4
        if (1, 5, 0) <= version <= (1, 5, 4):
            warnings.warn("your zstd version is between 1.5.0 and 1.5.4, which is not recommended due to a rare corruption bug in high compression mode, PLEASE UPGRADE TO 1.5.5+")
            print("sleeping for 20 seconds to let you read this message")
            time.sleep(20)

    def versionNumber(self) -> Tuple[int, int, int]:
        """
        Return runtime library version, the value is (`MAJOR`, `MINOR`, `RELEASE`).
        """
        rettext =  subprocess.check_output([self.bin_zstd, "-q", "-V"], shell=False).decode().strip()
        # 1.5.5
        ret_versions = [int(x) for x in rettext.split(".")]
        assert len(ret_versions) == 3
        return tuple(ret_versions) # type: ignore

    def compress_file(self, path: Union[str, Path], *, level: int = DEFAULT_LEVEL):
        ''' Compress path into path.zst and return the absolute path to the compressed file.

        we set -T0 to use all cores, --long=31 to use 2^31 (2GB) window size

        level:
            - 1 -> fast
            - ...
            - 19 -> high
            - ... (ultra mode)
            - 22 -> best
        '''
        if isinstance(path, str):
            path = Path(path)
        path = path.resolve() # remove trailing slash

        compressed_path = path.parent / (path.name + ".zst") # path + ".zst"
        compressed_path = compressed_path.resolve()

        compressing_temp_path = path.parent / (path.name + ".zst.tmp") # path + ".zst.tmp"
        compressing_temp_path = compressing_temp_path.resolve()

        if compressed_path.exists():
            print(f"File {compressed_path} already exists. Skip compressing.")
            return compressed_path

        cmd =  [self.bin_zstd, "-T0","-v", "--compress", "--force", "--long=31"]
        if level >= 20:
            cmd.append("--ultra")
        cmd.extend([f"-{level}", str(path), "-o", str(compressing_temp_path)])

        subprocess.run(cmd)
        assert compressing_temp_path.exists()
        # move tmp file to final file
        os.rename(compressing_temp_path, compressed_path)
        return compressed_path

    def test_integrity(self, path: Union[str, Path]) -> bool:
        ''' Test if path is a valid zstd compressed file. '''
        if isinstance(path, str):
            path = Path(path)
        path = path.resolve()
        r = subprocess.run([self.bin_zstd,"-vv", "-d", "-t", "--long=31", str(path)])
        return r.returncode == 0

class SevenZipCompressor:
    bin_7z = "7z"
    def __init__(self, bin_7z: str = "7z"):
        self.bin_7z = bin_7z
        retcode = subprocess.call([self.bin_7z, "-h"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if retcode:
            raise FileNotFoundError(f"7z binary not found at {self.bin_7z}")

    def compress_dir(self, dir_path: Union[str, Path], level: int = 0):
        ''' Compress dir_path into dump_dir.7z and return the resolved path to the compressed file. 
        
        level:
            - 0 -> only pack, no compression
            - 1 -> fast
            - ...
            - 9 -> ultra
        '''
        if isinstance(dir_path, str):
            dir_path = Path(dir_path)
        dir_path = dir_path.resolve() # remove trailing slash

        archive_path = dir_path.parent / (dir_path.name + ".7z") # dir_path + ".7z"
        archive_path = archive_path.resolve()

        archive_temp_path = dir_path.parent  / (dir_path.name + ".7z.tmp") # dir_path + ".7z.tmp"
        archive_temp_path = archive_temp_path.resolve()

        if archive_path.exists():
            print(f"File {archive_path} already exists. Skip compressing.")
            return archive_path

        if level:
            cmds = [self.bin_7z, "a", "-t7z", "-m0=lzma2", f"-mx={level}", "-scsUTF-8",
                "-md=64m", "-ms=off"]
        else: # level == 0
            assert level == 0
            cmds = [self.bin_7z, "a", "-t7z", f"-mx={level}", "-scsUTF-8", "-ms=off"]
        cmds.extend([str(archive_temp_path), str(dir_path)])

        r = subprocess.run(cmds, check=True)

        assert archive_temp_path.exists()
        # move tmp file to final file
        os.rename(archive_temp_path, archive_path)
        assert archive_path == archive_path.resolve()
        return archive_path
    
    def test_integrity(self, path: Union[str, Path]) -> bool:
        ''' Test if path is a valid 7z archive. '''
        if isinstance(path, str):
            path = Path(path)
        path = path.resolve()
        r = subprocess.run([self.bin_7z, "t", str(path)])
        return r.returncode == 0

if __name__ == "__main__":
    ZstdCompressor()
    SevenZipCompressor()