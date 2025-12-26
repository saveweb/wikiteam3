# Dump Types
There are three types of backups that can be made with `wikiteam3dumpgenerator`: **XML dumps**, **image dumps**, and **redirect dumps**.

## XML dump
An XML dump contains the entire history or the latest revision of all pages. To generate an XML dump, use the `--xml` option.

### Revisions
You can export all revisions (default) or the current revision only.

| Revisions | Option |
|-----------|--------|
| All | *None* |
| Current | `--curonly` |

### API
List of export APIs supported by wikiteam3:
 -  [Special:Export](https://www.mediawiki.org/wiki/Manual:Parameters_to_Special:Export) (default)
     -  First, get the list of page titles to export.
     -  Then, send POST requests to Special:Export to retrieve all/current revisions of pages in the list. The responses are in XML format.
 -  [API:Allrevisions](https://www.mediawiki.org/wiki/API:Allrevisions)
     -  Send GET requests to `api.php` with `action=query&list=allrevisions` to retrieve all/current revisions of all pages. The responses are then converted from JSON to XML.
     -  This API is significantly faster because it doesn't rely on the list of titles. You may disable delay between requests (`--delay 0`) if you are using this API.
 -  [API:Revisions](https://www.mediawiki.org/wiki/API:Revisions)
     -  First, get the list of page titles to export.
     -  Then, send GET requests to `api.php` with `action=query&format=xml&prop=revisions&titles=<title>` to retrieve all/current revisions of pages in the list. The responses are then converted from JSON to XML.
 -  [API:Query](https://www.mediawiki.org/wiki/API:Query) (DEVELOPMENT ONLY)
     -  First, get the list of page titles to export.
     -  Then, send GET requests to `api.php` with `action=query&titles=<title>&export=1` to retrieve the **current** revision of pages in the list. The exported data is in XML format.

If the list of page titles is needed, wikiteam3 tries [API:Allpages](https://www.mediawiki.org/wiki/API:Allpages) (1.8+) first. If it fails, wikiteam3 then tries to extract page titles from Special:Allpages.

**Limitations**: XML dumps produced using API:Allrevisions or API:Revisions are missing `<redirect>` tags, because these API don't return redirect information. Wikiteam3 introduced redirect dumps to retrieve redirect information. Unfortunately, currently there is no way to patch XML dumps using redirect information from redirect dumps, so the XML dumps will remain slightly flawed.

Here is a table for comparison. Legend:
 -  **MW version**: Supported MediaWiki versions. The use of old APIs enables wikiteam3 to create dumps for wikis running older versions of MediaWiki software.
 -  **Titles**: Requires a list of page titles to export before exporting.

| API | Option | MW version | Titles |
|-----|--------|------------|--------|
| Special:Export | *None* | 1.16+ (?) | Yes |
| API:Allrevisions | `--xmlrevisions` | 1.27+ | No |
| API:Revisions | `--xmlapiexport` | 1.8+ | Yes |
| API:Query | `--xmlrevisions_page` | 1.8+ | Yes |

TODO: Figure out the exact version for Special:Export

## Image dump
An image dump contains all files along with their metadata. It is called an *image* dump for historic reasons. To generate an image dump, use the `--images` option.

It takes three steps for the program to create an image dump:
1.  Get file names and metadata.
     -  If the API is available, try [API:Allimages](https://www.mediawiki.org/wiki/API:Allimages) (MW 1.13+) first. If it fails, use [API:Allpages](https://www.mediawiki.org/wiki/API:Allpages) (MW 1.8+).
     -  Otherwise, scrape and parse Special:Imagelist.
2.  Save file names and metadata at `<url>-<date>-images.txt`. The file format is documented at [`DEV.md`](https://github.com/saveweb/wikiteam3/blob/v4-main/DEV.md).
3.  Download the files. For each file, the actual size and SHA1 are checked against the API responses:
     -  If they match, the file would be saved at the `images` directory.
     -  Otherwise, the file would be saved at the `images_mismatch` directory, and an error message would be written to `errors.log`.

After creating an image dump, please check the `images_mismatch` directory. If files appear in this directory, that would be a problem. The probable cause is that the webmaster has turned on image compression for server responses. Please contact the webmaster.

TODO: File name limitations

## Redirect dump
A redirect dump contains a list of all redirects. The output file `<url>-<date>-redirects.jsonl` is in JSONL format, each line contains the infomation of one redirect, taken from the response of [API:Allredirects](https://www.mediawiki.org/wiki/API:Allredirects).

This feature is introduced in commit [`f901972`](https://github.com/saveweb/wikiteam3/commit/f901972ffc7525001f23cc20368d6437369c8953), due to limitations of some APIs. See section [XML dump](#xml-dump).

## References
 -  [WikiTeam tutorial](https://github.com/WikiTeam/wikiteam/wiki/Tutorial#dump-types)
 -  [WikiTeam](https://wiki.archiveteam.org/index.php/WikiTeam) at the ArchiveTeam Wiki
 -  [WikiTeam3 tutorial](https://meta.miraheze.org/wiki/Backups#WikiTeam3) at Miraheze Meta
