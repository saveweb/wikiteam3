# Dump Structure

Local directory structure:

```
<wiki>-<date>-wikidump
├── config.json
├── index.html
├── SpecialVersion.html
├── siteinfo.json
├── all_dumped.mark
├── uploaded_to_IA.mark
├── errors.log
├── <wiki>-<date>-titles.txt
├── <wiki>-<date>-current.xml
├── <wiki>-<date>-history.xml
├── <wiki>-<date>-images.txt
├── images
│   └── ...
├── images_mismatch
│   └── ...
└── <wiki>-<date>-redirects.jsonl
```

Internet Archive item structure:

```
wiki-<wiki>-<date>
├── <wiki>-<date>-dumpMeta
│   ├── config.json
│   ├── index.html
│   ├── SpecialVersion.html
│   ├── siteinfo.json
│   ├── errors.log
│   ├── <wiki>-<date>-titles.txt.zst
│   ├── <wiki>-<date>-images.txt.zst
│   └── <wiki>-<date>-redirects.jsonl.zst
├── <wiki>-<date>-history.xml.zst
├── <wiki>-<date>-images.7z
├── <wiki>-<date>-images_mismatch.7z
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
 -  `<wiki>-<date>-titles.txt`: List of titles.
 -  `<wiki>-<date>-current.xml`: The XML dump of current revision.
 -  `<wiki>-<date>-history.xml`: The XML dump of all revisions. See [Manual:Importing XML dumps](https://www.mediawiki.org/wiki/Manual:Importing_XML_dumps) for importing.

## Image Dump
 -  `<wiki>-<date>-images.txt`: Image metadata in TSV (Tab-Separated Values) format.
 -  `images` (directory): The image dump, i.e. the dump of all uploaded files.
 -  `<wiki>-<date>-images.7z`: Archive of the `images` directory without compression.
 -  `images_mismatch` (directory): Images whose actual size or SHA1 doesn't match API responses. Please contact the webmaster.
 -  `<wiki>-<date>-images_mismatch.7z`: Archive of the `images_mismatch` directory without compression.

## Redirects Dump
 -  `<wiki>-<date>-redirects.jsonl`: The redirects dump. Each line contains one redirection.

## Notes
 -  `<wiki>` - formatted wiki URL
 -  `<date>` - date in UTC
