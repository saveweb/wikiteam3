# Dump Structure

```
<url>-<date>-wikidump
├── images
│   └── ...
├── images_mismatch
│   └── ...
├── config.json
├── <url>-<date>-titles.txt
├── <url>-<date>-history.xml
├── <url>-<date>-images.txt
├── index.html
├── SpecialVersion.html
├── siteinfo.json
├── all_dumped.mark
└── errors.log
```

```
wiki-<url>-<date>
├── <url>-<date>-dumpMeta
│   ├── config.json
│   ├── index.html
│   ├── SpecialVersion.html
│   ├── siteinfo.json
│   ├── errors.log
│   └── ...
├── x
├── x
├── x
└── x
```


## General
 -  `config.json`: Dump configuration. Used when [resuming an incomplete dump](https://github.com/saveweb/wikiteam3/blob/v4-main/README.md#resuming-an-incomplete-dump).
 -  `index.html`: Archive of `index.php` (the main page).
 -  `SpecialVersion.html`: Archive of `[[Special:Version]]`.
 -  `siteinfo.json`: Archive of Siteinfo API response.
 -  `all_dumped.mark`: Marks the end of the dump. Content: `<time>:<msg>`
 -  `errors.log`: Errors log. Please check this file after the dump is finished.

## XML Dump
 -  `<url>-<date>-titles.txt`: List of titles.
 -  `<url>-<date>-history.xml`: The XML dump. See [Manual:Importing XML dumps](https://www.mediawiki.org/wiki/Manual:Importing_XML_dumps) for importing.

## Image Dump
 -  `images` (directory): The image dump, i.e. the dump of all uploaded files.
 -  `images_mismatch` (directory): Images whose actual size or SHA1 doesn't match API responses. Please contact the webmaster.
 -  `<url>-<date>-images.txt`: Image metadata in TSV (Tab-Separated Values) format.

## Redirects Dump
