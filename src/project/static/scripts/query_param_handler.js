function getQueryParams() {
    return new URLSearchParams(window.location.search);
}

function removeDuplicatePageParams(params) {
    const filteredParams = new URLSearchParams();
    params.forEach((value, key) => {
        if (key !== 'page') {
            filteredParams.append(key, value);
        }
    });
    return filteredParams;
}

function appendAllQueryParams(url) {
    const params = getQueryParams();
    const queryParams = removeDuplicatePageParams(params).toString();

    if (queryParams) {
        const separator = url.includes('?') ? '&' : '?';
        return `${url}${separator}${queryParams}`;
    }
    return url;
}

document.querySelectorAll('a').forEach(link => {
    const href = link.getAttribute('href');
    if (href && href.startsWith('/') && !href.startsWith('//')) {
        link.setAttribute('href', appendAllQueryParams(href));
    }
});
