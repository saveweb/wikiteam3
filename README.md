# `wikiteam3`

> Countless MediaWikis are still waiting to be archived.

`wikiteam3` is a fork of `mediawiki-scraper`.

## Why we fork mediawiki-scraper

Originally, mediawiki-scraper was named wikiteam3, but wikiteam upstream (py2 version) suggested that the name should be changed to avoid confusion with the original wikiteam.  
Half a year later, we didn't see any py3 porting progress in the original wikiteam, and mediawiki-scraper lacks "code" reviewers.  
So, we decided to break that suggestion, fork and named it back to wikiteam3, put the code here, and release it to pypi wildly.

Everything still under GPLv3 license.

## wikiteam3 Toolset

wikiteam3 is a set of tools for archiving wikis. The main general-purpose module of wikiteam3 is dumpgenerator, which can download XML dumps of MediaWiki sites that can then be parsed or redeployed elsewhere.

## Installation

```shell
pip install wikiteam3
```

## Usage

TODO: move usage to a separate doc

### Downloading a wiki with complete XML history and images

```bash
dumpgenerator http://wiki.domain.org --xml --images
```

### Manually specifying `api.php` and/or `index.php`

If the script can't find itself the `api.php` and/or `index.php` paths, then you can provide them:

```bash
dumpgenerator --api http://wiki.domain.org/w/api.php --xml --images
```

```bash
dumpgenerator --api http://wiki.domain.org/w/api.php --index http://wiki.domain.org/w/index.php \
    --xml --images
```

If you only want the XML histories, just use `--xml`. For only the images, just `--images`. For only the current version of every page, `--xml --curonly`.

### Resuming an incomplete dump

```bash
dumpgenerator \
    --api http://wiki.domain.org/w/api.php --xml --images --resume --path /path/to/incomplete-dump
```

In the above example, `--path` is only necessary if the download path is not the default.

`dumpgenerator` will also ask you if you want to resume if it finds an incomplete dump in the path where it is downloading.

## Using `uploader`

TODO: ...

## Checking dump integrity

TODO: move to a separate doc

If you want to check the XML dump integrity, type this into your command line to count title, page and revision XML tags:

```bash
grep -E '<title(.*?)>' *.xml -c;grep -E '<page(.*?)>' *.xml -c;grep \
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

## Publishing the dump

Please consider publishing your wiki dump(s). You can do it yourself as explained at WikiTeam's [Publishing the dump](https://github.com/WikiTeam/wikiteam/wiki/Tutorial#Publishing_the_dump) tutorial.

## Contributors

**WikiTeam** is the [Archive Team](http://www.archiveteam.org) [[GitHub](https://github.com/ArchiveTeam)] subcommittee on wikis.
It was founded and originally developed by [Emilio J. Rodríguez-Posada](https://github.com/emijrp), a Wikipedia veteran editor and amateur archivist. Thanks to people who have helped, especially to: [Federico Leva](https://github.com/nemobis), [Alex Buie](https://github.com/ab2525), [Scott Boyd](http://www.sdboyd56.com), [Hydriz](https://github.com/Hydriz), Platonides, Ian McEwen, [Mike Dupont](https://github.com/h4ck3rm1k3), [balr0g](https://github.com/balr0g) and [PiRSquared17](https://github.com/PiRSquared17).

**Mediawiki-Scraper** The Python 3 initiative is currently being led by [Elsie Hupp](https://github.com/elsiehupp), with contributions from [Victor Gambier](https://github.com/vgambier), [Thomas Karcher](https://github.com/t-karcher), [Janet Cobb](https://github.com/randomnetcat), [yzqzss](https://github.com/yzqzss), [NyaMisty](https://github.com/NyaMisty) and [Rob Kam](https://github.com/robkam)

**WikiTeam3** None yet.
