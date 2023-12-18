# `wikiteam3`

<!-- !["MediaWikiArchive.png"](./MediaWikiArchive.png) -->
<div align=center><img width = '150' height ='150' src ="./MediaWikiArchive.png"/></div>

> Countless MediaWikis are still waiting to be archived.
>
> _Image by [@gledos](https://github.com/gledos/)_

`wikiteam3` is a fork of `mediawiki-scraper`.

<details>

## Why we fork mediawiki-scraper

Originally, mediawiki-scraper was named wikiteam3, but wikiteam upstream (py2 version) suggested that the name should be changed to avoid confusion with the original wikiteam.  
Half a year later, we didn't see any py3 porting progress in the original wikiteam, and mediawiki-scraper lacks "code" reviewers.  
So, we decided to break that suggestion, fork and named it back to wikiteam3, put the code here, and release it to pypi wildly.

Everything still under GPLv3 license.

</details>

## Installation/Upgrade

```shell
pip install wikiteam3 --upgrade
```

## Dumpgenerator usage

### Downloading a wiki with complete XML history and images

```bash
wikiteam3dumpgenerator http://wiki.domain.org --xml --images
```

>[!WARNING]
>
> `NTFS/Windows` users please note: When using `--images`, because NTFS does not allow characters such as `:*?"<>|` in filenames, some files may not be downloaded, please pay attention to the `XXXXX could not be created by OS` error in your `errors.log`.
> We will not make special treatment for NTFS/EncFS "path too long/illegal filename", highly recommend you to use ext4/xfs/btrfs, etc.
> <details>
> - Introducing the "illegal filename rename" mechanism will bring complexity. WikiTeam(python2) had this before, but it caused more problems, so it was removed in WikiTeam3.
> - It will cause confusion to the final user of wikidump (usually the Wiki site administrator).
> - NTFS is not suitable for large-scale image dump with millions of files in a single directory.(Windows background service will occasionally scan the whole disk, we think there should be no users using WIN/NTFS to do large-scale MediaWiki archive)
> - Using other file systems can solve all problems.
> </details>

### Manually specifying `api.php` and/or `index.php`

If the script can't find itself the `api.php` and/or `index.php` paths, then you can provide them:

```bash
wikiteam3dumpgenerator --api http://wiki.domain.org/w/api.php --xml --images
```

```bash
wikiteam3dumpgenerator --api http://wiki.domain.org/w/api.php --index http://wiki.domain.org/w/index.php \
    --xml --images
```

If you only want the XML histories, just use `--xml`. For only the images, just `--images`. For only the current version of every page, `--xml --curonly`.

### Resuming an incomplete dump

<details>

```bash
wikiteam3dumpgenerator \
    --api http://wiki.domain.org/w/api.php --xml --images --resume --path /path/to/incomplete-dump
```

In the above example, `--path` is only necessary if the download path (wikidump dir) is not the default.

>[!NOTE]
>
> en: When resuming an incomplete dump, the configuration in `config.json` will override the CLI parameters. (But not all CLI parameters will be ignored, check `config.json` for details)

`wikiteam3dumpgenerator` will also ask you if you want to resume if it finds an incomplete dump in the path where it is downloading.

</details>

## Using `wikiteam3uploader`

### Requirements

> [!NOTE]
>
> Please make sure you have the following requirements before using `wikiteam3uploader`, and you don't need to install them if you don't wanna upload the dump to IA.

- unbinded localhost port 62954 (for multiple processes compressing queue)
- 3GB+ RAM (~2.56GB for commpressing)
- 64-bit OS (required by 2G `wlog` size)

- `7z` (binary)
    > Debian/Ubuntu: install `p7zip-full`  

    > [!NOTE]
    >
    > Windows: install <https://7-zip.org> and add `7z.exe` to PATH
- `zstd` (binary)
    > 1.5.5+ (recommended), v1.5.0-v1.5.4(DO NOT USE), 1.4.8 (minimum)  
    > install from <hhttps://github.com/facebook/zstd>  

    > [!NOTE]
    >
    > Windows: add `zstd.exe` to PATH

### Uploader usage

> [!NOTE]
>
> Read `wikiteam3uploader --help` and do not forget `~/.wikiteam3_ia_keys.txt` before using `wikiteam3uploader`.

```bash
wikiteam3uploader {YOUR_WIKI_DUMP_PATH}
```

## Checking dump integrity

TODO: xml2titles.py

If you want to check the XML dump integrity, type this into your command line to count title, page and revision XML tags:

```bash
grep -E '<title(.*?)>' *.xml -c; grep -E '<page(.*?)>' *.xml -c; grep \
    "</page>" *.xml -c;grep -E '<revision(.*?)>' *.xml -c;grep "</revision>" *.xml -c
```

You should see something similar to this (not the actual numbers) - the first three numbers should be the same and the last two should be the same as each other:

```bash
580
580
580
5677
5677
```

If your first three numbers or your last two numbers are different, then, your XML dump is corrupt (it contains one or more unfinished ```</page>``` or ```</revision>```). This is not common in small wikis, but large or very large wikis may fail at this due to truncated XML pages while exporting and merging. The solution is to remove the XML dump and re-download, a bit boring, and it can fail again.

## import wikidump to MediaWiki / wikidump data tips

> [!IMPORTANT]
>
> In the article name, spaces and underscores are treated as equivalent and each is converted to the other in the appropriate context (underscore in URL and database keys, spaces in plain text). <https://www.mediawiki.org/wiki/Manual:Title.php#Article_name>

> [!NOTE]
>
> `WikiTeam3` uses `zstd` to compress `.xml` and `.txt` files, and `7z` to pack images (media files).  
> `zstd` is a very fast stream compression algorithm, you can use `zstd -d` to decompress `.zst` file/steam.

## Contributors

**WikiTeam** is the [Archive Team](http://www.archiveteam.org) [[GitHub](https://github.com/ArchiveTeam)] subcommittee on wikis.
It was founded and originally developed by [Emilio J. Rodríguez-Posada](https://github.com/emijrp), a Wikipedia veteran editor and amateur archivist. Thanks to people who have helped, especially to: [Federico Leva](https://github.com/nemobis), [Alex Buie](https://github.com/ab2525), [Scott Boyd](http://www.sdboyd56.com), [Hydriz](https://github.com/Hydriz), Platonides, Ian McEwen, [Mike Dupont](https://github.com/h4ck3rm1k3), [balr0g](https://github.com/balr0g) and [PiRSquared17](https://github.com/PiRSquared17).

**Mediawiki-Scraper** The Python 3 initiative is currently being led by [Elsie Hupp](https://github.com/elsiehupp), with contributions from [Victor Gambier](https://github.com/vgambier), [Thomas Karcher](https://github.com/t-karcher), [Janet Cobb](https://github.com/randomnetcat), [yzqzss](https://github.com/yzqzss), [NyaMisty](https://github.com/NyaMisty) and [Rob Kam](https://github.com/robkam)

**WikiTeam3** Every archivist who has uploaded a wikidump to the [Internet Archive](https://archive.org/search?query=subject%3Awikiteam3).
