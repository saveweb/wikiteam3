# Tutorial
Welcome! You are probably learning how to archive your favorite wiki using wikiteam3.

Before we get started, please answer these questions:

## Do I really need wikiteam3?
### Do you have direct shell access to the server?
If you have direct shell access to the server, the best option is to backup all server files (see [Manual:Backing up a wiki](https://www.mediawiki.org/wiki/Manual:Backing_up_a_wiki)).

Wikiteam3 can only backup public pages and files, it cannot backup deleted pages, logs, user preferences...

### Can wikiteam help you do this favor?
<!-- This paragraph is taken from README.md -->
WikiTeam is always willing to help! For public MediaWiki, there is no need to run wikiteam3 by yourself. You can send an archive request to the [**WikiTeam IRC channel**](https://chat.hackint.org/?join=%23wikiteam) ([logs](https://irclogs.archivete.am/wikiteam)). Please include the archive reason in your request (e.g. the wiki is about to shutdown, a wikidump is needed to migrate to another wikifarm, etc.). An online member will run a [wikibot](https://wikibot.digitaldragon.dev/) job for your request.

If the wiki is private, you would have to run wikiteam3 by yourself:

### Is the wiki powered by MediaWiki?
Is the wiki you want to archive powered by MediaWiki?

Most wikis powered by MediaWiki have a banner at the bottom-right corner. There is also a list of [sites using MediaWiki](https://www.mediawiki.org/wiki/Sites_using_MediaWiki) at MediaWiki.org.

If the wiki is not powered by MediaWiki, you would have to use dedicated tools for other wikis. For DokuWiki, try [DokuWiki Dumper](https://github.com/saveweb/dokuwiki-dumper); for PukiWiki, try [PukiWiki Dumper](https://github.com/saveweb/pukiwiki-dumper).

## Install wikiteam3
Wikiteam3 is a Python package. There is a detailed tutorial for [installing packages](https://packaging.python.org/en/latest/tutorials/installing-packages/) at Python Packaging User Guide. Please follow it to install Python (if you haven't installed) and wikiteam3.

Key points:

First, install Python 3 if you haven't installed it. Make sure you can run both Python and pip from the command line:

```console
$ python3 --version
$ python3 -m pip --version
```

If you are a user, you can simply install wikiteam3 from [pip](https://pypi.org/project/wikiteam3/). However, it is recommended to install wikiteam3 in a *virtual environment*, which isolates wikiteam3 and other Python packages.

```console
$ python3 -m pip install wikiteam3
```

> [!NOTE]
> If you are a developer, it is recommended to clone wikiteam3 from [GitHub](https://github.com/saveweb/wikiteam3), and install it in *editable mode*.

## Run wikiteam3
If you have installed wikiteam3 correctly, a help message would appear if you run the following message:

```console
$ wikiteam3dumpgenerator --help
```

Here we will use the [ArchiveTeam Wiki](https://wiki.archiveteam.org/index.php/Main_Page) as an example.

### Find out the entry point URLs
Wikiteam3 needs the entry point URLs of `api.php` and `index.php` to archive a wiki. If you only provide the URL to the wiki, wikiteam3 will try to guess the entry point URLs, which can sometimes fail. A safer way is to provide the entry point URLs.

First, navigate to the "Special:Version" special page. You can simply type "Special:Version" in the search box and hit "Enter".

Then, scroll to section "Entry point URLs", and copy the entry points of `api.php` and `index.php`. In our example, the URL of `api.php` is `https://wiki.archiveteam.org/api.php`, and the URL of `index.php` is `https://wiki.archiveteam.org/index.php`.

### Determine the type of dump you want
Wikiteam3 currently supports three types of dumps: XML dumps, image dumps, and redirect dumps.

For more information, read the "Dump Types" page.

It is recommended to include all of them: `--xml --xmlrevisions --images --redirects`.

### Start dumping
Open the terminal, and `cd` to where you would save your dump. If you installed wikiteam3 in a virtual environment, activate it. Then run wikiteam3 with the arguments you selected.

In our example, here are the arguments:
```console
$ wikiteam3dumpgenerator \
  --api 'https://wiki.archiveteam.org/api.php' \
  --index 'https://wiki.archiveteam.org/index.php' \
  --xml --xmlrevisions \
  --images \
  --redirects
```

Wikiteam3 will create a directory named `<url>-<date>-wikidump`.

### Check your dump
#### Checking dump integrity
<!-- This section is taken from README.md -->

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

---

The above method roughly ensures that the XML dump is not damaged. To make sure that the dump applies to the schema, use `xmllint`:

```console
$ xmllint --schema export-0.11-wikiteam3.xsd path/to/<url>-<date>-history.xml --noout
<url>-<date>-history.xml validates
```

`export-0.11-wikiteam3.xsd` is a modified version of the official `export-0.11.xsd` schema.

Please report errors.

#### Fix errors
Open `errors.log` and fix them.

### Upload your dump to the Internet Archive (optional)
See [README](https://github.com/saveweb/wikiteam3/blob/v4-main/README.md#using-wikiteam3uploader).
