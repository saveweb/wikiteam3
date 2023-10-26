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

### XML dump

- MediaWiki's page export format: <https://www.mediawiki.org/xml/>.
- MediaWiki 的 `importDump.php` 目前(1.40.1) 仍并不实际读取 `<text>` 的属性值，因此 `deleted="deleted"` 会创建一个空 rev 而不是“被删除的” rev。
- 在早前的 WikiTeam 版本中，XML dump 中的 `<sha1>` 标签会被移除，这会导致重新导入 MediaWiki 时，MediaWiki 无从知晓 rev 是否已经存在，从而重复导入已有 revision。建议您可以根据 `<text>` 的 `sha1` 属性重建 `<sha1>` 标签，以避免重复导入。
- `--xmlrevisions` 抓取期间如果有页面发生移动甚至合并历史。导入后，其页面历史可能会不能理解。<details> WikiTean 生成的一部分 XML dump 是使用近乎标准的 page by page 的 page export format，保证 page title 的唯一性，但现在为了减少源站压力、加速爬取，WikiTeam3 的 `--xmlrevisions*` 会以 `timestamp`/`rev_id` 为升序组织 XML dump（基本相当于以时间升序输出 revisions 表），所以同一个 title 可能会有多个 `<page>`。MediaWiki 可以正常导入这种 XML dump，但如果在 WikiTeam3 抓取源站的过程中，源站的 page title 发生了变化/重定向， </details>
- 页面

### Images(Files) dump

> [!IMPORTANT]
>
> MediaWiki 的 file repo [始终使用下划线形式的文件名](https://www.mediawiki.org/wiki/Manual:Image_table#Fields)，而在 wikiteam(py2) 以及 WikiTeam3 早期版本中，是用的空格形式的文件名。这会导致在导入后，MediaWiki 无法定位到任何带有下划线的文件名。因此，请将所有的文件名中的空格重命名成下划线！
- WikiTeam 早期版本不在 images.txt 中记录文件 sha1、size 等元信息，且不验证已下载文件的完整性。小心 HTTP 错误页面。

## Contributors

**WikiTeam** is the [Archive Team](http://www.archiveteam.org) [[GitHub](https://github.com/ArchiveTeam)] subcommittee on wikis.
It was founded and originally developed by [Emilio J. Rodríguez-Posada](https://github.com/emijrp), a Wikipedia veteran editor and amateur archivist. Thanks to people who have helped, especially to: [Federico Leva](https://github.com/nemobis), [Alex Buie](https://github.com/ab2525), [Scott Boyd](http://www.sdboyd56.com), [Hydriz](https://github.com/Hydriz), Platonides, Ian McEwen, [Mike Dupont](https://github.com/h4ck3rm1k3), [balr0g](https://github.com/balr0g) and [PiRSquared17](https://github.com/PiRSquared17).

**Mediawiki-Scraper** The Python 3 initiative is currently being led by [Elsie Hupp](https://github.com/elsiehupp), with contributions from [Victor Gambier](https://github.com/vgambier), [Thomas Karcher](https://github.com/t-karcher), [Janet Cobb](https://github.com/randomnetcat), [yzqzss](https://github.com/yzqzss), [NyaMisty](https://github.com/NyaMisty) and [Rob Kam](https://github.com/robkam)

**WikiTeam3** None yet.
