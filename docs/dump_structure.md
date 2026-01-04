# Dump Structure

Local directory structure:

```
<url>-<date>-wikidump
├── config.json
├── index.html
├── SpecialVersion.html
├── siteinfo.json
├── all_dumped.mark
├── uploaded_to_IA.mark
├── errors.log
├── <url>-<date>-titles.txt
├── <url>-<date>-history.xml
├── <url>-<date>-images.txt
├── images
│   └── ...
├── images_mismatch
│   └── ...
└── <url>-<date>-redirects.jsonl
```

Internet Archive item structure:

```
wiki-<url>-<date>
├── <url>-<date>-dumpMeta
│   ├── config.json
│   ├── index.html
│   ├── SpecialVersion.html
│   ├── siteinfo.json
│   ├── errors.log
│   ├── <url>-<date>-titles.txt.zst
│   ├── <url>-<date>-images.txt.zst
│   └── <url>-<date>-redirects.jsonl.zst
├── <url>-<date>-history.xml.zst
├── <url>-<date>-images.7z
├── <url>-<date>-images_mismatch.7z
└── <identifier>_logo.<suffix>
```

## General
 -  `config.json`: Dump configuration. Used when [resuming an incomplete dump](https://github.com/saveweb/wikiteam3/blob/v4-main/README.md#resuming-an-incomplete-dump).
 -  `index.html`: Archive of `index.php` (the main page).
 -  `SpecialVersion.html`: Archive of `[[Special:Version]]`.
 -  `siteinfo.json`: Archive of Siteinfo API response.
 -  `all_dumped.mark`: Marks the end of the dump. Content: `<time>:<msg>`
 -  `uploaded_to_IA.mark`: Marks the success upload to IA. Content: `<time>: identifier: <identifier>`
 -  `errors.log`: Errors log. Please check this file after the dump is finished.
 -  `<identifier>_logo.<suffix>`: Logo. This is downloaded when uploading to IA, and would not be stored locally.

## XML Dump
 -  `<url>-<date>-titles.txt`: List of titles.
 -  `<url>-<date>-history.xml`: The XML dump. See [Manual:Importing XML dumps](https://www.mediawiki.org/wiki/Manual:Importing_XML_dumps) for importing.

## Image Dump
 -  `<url>-<date>-images.txt`: Image metadata in TSV (Tab-Separated Values) format.
 -  `images` (directory): The image dump, i.e. the dump of all uploaded files.
 -  `<url>-<date>-images.7z`: Compression of the `images` directory.
 -  `images_mismatch` (directory): Images whose actual size or SHA1 doesn't match API responses. Please contact the webmaster.
 -  `<url>-<date>-images_mismatch.7z`: Compression of the `images_mismatch` directory.

## Redirects Dump
 -  `<url>-<date>-redirects.jsonl`: The redirects dump. Each line contains one redirection.
