function getQueryParams() {
    return new URLSearchParams(window.location.search);
}

function removePageParam(params) {
    params.delete('page');
    return params;
}

function applyQueryParams(url) {
    const params = removePageParam(getQueryParams());
    if (params.toString()) {
        return `${url}${url.includes('?') ? '&' : '?'}${params.toString()}`;
    }
    return url;
}

document.querySelectorAll('a[href^="/"]:not([href^="//"])').forEach(link => {
    link.setAttribute('href', applyQueryParams(link.getAttribute('href')));
});
