import yt_dlp
from yt_dlp.compat import compat_basestring, compat_urllib_parse, compat_urllib_request
from yt_dlp.utils import HEADRequest, PUTRequest, sanitized_Request

_original_urlopen = yt_dlp.YoutubeDL.urlopen


def _patched_urlopen(self, req):
    """Start an HTTP download"""
    if isinstance(req, compat_basestring):
        req = sanitized_Request(req)
    # an embedded /../ sequence is not automatically handled by urllib2
    # see https://github.com/yt-dlp/yt-dlp/issues/3355
    url = req.get_full_url()
    parts = url.partition("/../")
    if parts[1]:
        url = compat_urllib_parse.urljoin(
            parts[0] + parts[1][:1], parts[1][1:] + parts[2]
        )
    if url:
        # worse, URL path may have initial /../ against RFCs: work-around
        # by stripping such prefixes, like eg Firefox
        parts = compat_urllib_parse.urlsplit(url)
        path = parts.path
        while path.startswith("/../"):
            path = path[3:]
        url = parts._replace(path=path).geturl()
        # get a new Request with the munged URL
        if url != req.get_full_url():
            req_type = {"HEAD": HEADRequest, "PUT": PUTRequest}.get(
                req.get_method(), compat_urllib_request.Request
            )
            req = req_type(
                url,
                data=req.data,
                headers=dict(req.header_items()),
                origin_req_host=req.origin_req_host,
                unverifiable=req.unverifiable,
            )
    return self._opener.open(req, timeout=self._socket_timeout)


yt_dlp.YoutubeDL.urlopen = _patched_urlopen
