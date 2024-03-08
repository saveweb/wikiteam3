
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Tuple, Union
import warnings


class ZstdCompressor:
    DEFAULT_LEVEL = 17
    MIN_VERSION = (1, 4, 8)
    bin_zstd = "zstd"

    # additional options
    rezstd: bool = False
    rezstd_endpoint: str = "http://pool-rezstd.saveweb.org/rezstd/"

    def __init__(self, bin_zstd: str = "zstd",
                 rezstd: bool = False, rezstd_endpoint: str = "http://pool-rezstd.saveweb.org/rezstd/"):
        """
        bin_zstd: path to zstd binary
        rezstd: upload zstd pre-compressed file to rezstd server for recompression with "best" (-22 --ultra --long=31) configuration.
        rezstd_endpoint: the endpoint of rezstd server 
        """
        self.bin_zstd = bin_zstd
        version = self.versionNumber()
        assert version >= self.MIN_VERSION, f"zstd version must be >= {self.MIN_VERSION}"
        # if v1.5.0-v1.5.4
        if (1, 5, 0) <= version <= (1, 5, 4):
            warnings.warn("your zstd version is between 1.5.0 and 1.5.4, which is not recommended due to a rare corruption bug in high compression mode, PLEASE UPGRADE TO 1.5.5+")
            sys.exit(1)

        self.rezstd = rezstd
        self.rezstd_endpoint = rezstd_endpoint

    def versionNumber(self) -> Tuple[int, int, int]:
        """
        Return runtime library version, the value is (`MAJOR`, `MINOR`, `RELEASE`).
        """
        rettext =  subprocess.check_output([self.bin_zstd, "-q", "-V"], shell=False).decode().strip()
        # 1.5.5
        ret_versions = [int(x) for x in rettext.split(".")]
        assert len(ret_versions) == 3
        return tuple(ret_versions) # type: ignore

    def compress_file(self, path: Union[str, Path], *, level: int = DEFAULT_LEVEL, long_level: int = 31) -> Path:
        ''' Compress path into path.zst and return the absolute path to the compressed file.

        we set -T0 to use all cores

        level:
            - 1 -> fast
            - ...
            - 19 -> high
            - ... (ultra mode)
            - 22 -> best
        long_level:
            - 31 -> 2^31 (2GB) window size (default)
            - 30 -> 2^30 (1GB)
            - ...
            - 0 -> Disable --long flag
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

        cmd =  [self.bin_zstd, "-T0","-v", "--compress", "--force"]
        if level >= 20:
            cmd.append("--ultra")
        if long_level:
            cmd.append(f"--long={long_level}")
        cmd.extend([f"-{level}", str(path), "-o", str(compressing_temp_path)])

        subprocess.run(cmd)
        assert compressing_temp_path.exists()
        if self.rezstd:
            pre_compressing_temp_path = compressing_temp_path # alias

            compressing_rezstded_temp_path = path.parent / (path.name + ".rezstded.tmp")
            compressing_rezstded_temp_path = compressing_rezstded_temp_path.resolve()

            assert self.rezstd_endpoint.endswith("/")
            import requests
            session = requests.Session()
            # upload to rezstd
            print("Creating rezstd task...")
            # TODO: reuse previous task_id
            r = session.post(self.rezstd_endpoint + 'create/chunked')
            print(r.text)
            task_id = r.json()["task_id"]
            # upload chunks
            total_size = pre_compressing_temp_path.stat().st_size
            chunk_size = 1024 * 1024 * 50 # 50MB
            with open(pre_compressing_temp_path, "rb") as f:
                # /rezstd/upload/chunked/:task_id/:chunk_id
                upload_bytes = 0
                chunk_id = 0
                while chunk := f.read(chunk_size):
                    # TODO: parrallel upload
                    r = session.put(self.rezstd_endpoint + f"upload/chunked/{task_id}/{chunk_id}", files={"chunk": chunk})
                    assert "error" not in r.json()
                    upload_bytes += len(chunk)
                    print(f"Uploaded {upload_bytes/1024/1024:.2f}/{total_size/1024/1024:.2f} MB", end="\r")
                    chunk_id += 1
            print()
            # r.POST("/rezstd/concat/chunked/:task_id/:max_chunk_id/:total_size"
            print("Concatenating chunks...")
            max_chunk_id = chunk_id - 1 or 0
            r = session.post(self.rezstd_endpoint + f"concat/chunked/{task_id}/{max_chunk_id}/{total_size}")
            print(r.text)
            assert "error" not in r.json()

            os.remove(pre_compressing_temp_path)
            finished = False
            while not finished:
                r = session.get(self.rezstd_endpoint + f"status/{task_id}")
                print(r.text, end="\r")
                assert "error" not in r.json()
                if r.json()["status"] == "finished":
                    finished = True
                    break
                time.sleep(5)
            print("Server side recompression finished, log:",
                  f"{self.rezstd_endpoint}log/{task_id}",
                  "(only available for a few days)")
            r = session.get(self.rezstd_endpoint + f"download/{task_id}/wikiteam3_task.zst", stream=True)
            content_length = int(r.headers["Content-Length"])
            with open(compressing_rezstded_temp_path, "wb") as f:
                written = 0
                last_report_time = time.time()
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if time.time() - last_report_time > 10:
                        print(f"Downloaded {written/1024/1024:.2f}/{content_length/1024/1024:.2f} MB", end="\r")
                        last_report_time = time.time()
                    f.write(chunk)
                    written += len(chunk)
            print()
            # print("Download finished, deleting from server...")
            # r = session.delete(self.rezstd_endpoint + f"delete/{task_id}")
            # print(r.text)
            # assert "error" not in r.json()
            os.rename(compressing_rezstded_temp_path, compressing_temp_path)

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