# Design

## Canonical redirect rule

Operational mutations should follow one simple contract:

1. trust the referer first when it is safe
2. otherwise fall back to the named route for that role workspace
3. keep fragment append behavior separate from route selection

## Route ownership

The action view should own only:

1. which role workspace is the safe fallback
2. whether a fragment should be appended

It should not own:

1. handwritten URL path strings
2. route spelling details

## Readability rule

The file should read like:

- manager action -> manager workspace
- coach action -> coach workspace
- reception action -> reception workspace

That way the code explains intent instead of memorizing street names.

## Residual tolerance

If `_redirect_back()` still takes a concrete URL string after `reverse()`, that is acceptable.
The debt is the handwritten path literal, not the redirect helper signature.
