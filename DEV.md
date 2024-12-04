# Snippets

## API Output format

https://www.mediawiki.org/wiki/API:Data_formats#Output

> The standard and default output format in MediaWiki is JSON. All other formats are discouraged.
> 
> The output format should always be specified using format=yourformat with yourformat being one of the following:
> 
>     json: JSON format. (recommended)
>     php: serialized PHP format. (deprecated)
>     xml: XML format. (deprecated)
>     txt: PHP print_r() format. (removed in 1.27)
>     dbg: PHP var_export() format. (removed in 1.27)
>     yaml: YAML format. (removed in 1.27)
>     wddx: WDDX format. (removed in 1.26)
>     dump: PHP var_dump() format. (removed in 1.26)
>     none: Returns a blank response. 1.21+

In our practice, `json` is not available for some old wikis.

## Allpages

https://www.mediawiki.org/wiki/API:Allpages (>= 1.8)


## Allimages

https://www.mediawiki.org/wiki/API:Allimages (>= 1.13)

## Redirects

https://www.mediawiki.org/wiki/Manual:Redirect_table

## Logs

https://www.mediawiki.org/wiki/Manual:Logging_table

## Continuation

https://www.mediawiki.org/wiki/API:Continue (≥ 1.26)
https://www.mediawiki.org/wiki/API:Raw_query_continue (≥ 1.9)

> From MediaWiki 1.21 to 1.25, it was required to specify continue= (i.e. with an empty string as the value) in the initial request to get continuation data in the format described above. Without doing that, API results would indicate there is additional data by returning a query-continue element, explained in Raw query continue.
> Prior to 1.21, that raw continuation (`query-continue`) was the only option.
> 
> If your application needs to use the raw continuation in MediaWiki 1.26 or later, you must specify rawcontinue= to request it. 

# Workarounds

## truncated API response causes infinite loop

https://github.com/mediawiki-client-tools/mediawiki-dump-generator/issues/166
https://phabricator.wikimedia.org/T86611

wikiteam3 workaround: https://github.com/saveweb/wikiteam3/commit/76465d34898b80e8c0eb6d9652aa8efa403a7ce7

## MWUnknownContentModelException

> "The content model xxxxxx is not registered on this wiki;"

Some extensions use custom content models for their own purposes, but they did not register a handler to export their content.

wikiteam3 workaround: https://github.com/saveweb/wikiteam3/commit/fd5a02a649dcf3bdab7ac1268445b0550130e6ee

## Insecure SSL

https://docs.openssl.org/1.1.1/man1/ciphers/
https://docs.openssl.org/master/man1/openssl-ciphers/

workaround: https://github.com/DigitalDwagon/wikiteam3/blob/8a054882de19c6b69bc03798d3044b7b5c4c3c88/wikiteam3/utils/monkey_patch.py#L63-L84