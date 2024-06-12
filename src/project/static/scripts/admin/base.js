function search() {
    const searchQuery = document.getElementById("search").value;

    const paramsArray = getExistingParams(["search", "page"]);

    if (searchQuery !== "") paramsArray.unshift(`search=${encodeURIComponent(searchQuery)}`);

    addParamsToUrl(paramsArray);
}

function getExistingParams(excludedParams) {
    const urlParams = new URLSearchParams(window.location.search);
    let paramsArray = [];

    for (let param of urlParams) {
        if (!excludedParams.includes(param[0])) {
            paramsArray.push(`${param[0]}=${encodeURIComponent(param[1])}`);
        }
    }
    return paramsArray;
}

function addParamsToUrl(paramsArray) {
    const paramsString = paramsArray.length > 0 ? "?" + paramsArray.join("&") : "";
    const baseUrl = window.location.href.split("?")[0];
    const newUrl = baseUrl + paramsString;
    window.location.href = newUrl;
}

function getQueryParams() {
    params = new URLSearchParams(window.location.search);
    params.delete("type");
    params.delete("msg");
    return params;
}

function removePageParam(params) {
    params.delete("page");
    return params;
}

function applyQueryParams(url) {
    const params = removePageParam(getQueryParams());
    if (params.toString()) {
        return `${url}${url.includes("?") ? "&" : "?"}${params.toString()}`;
    }
    return url;
}

document.querySelectorAll('a[href^="/"]:not([href^="//"])').forEach((link) => {
    if (!link.getAttribute("href").includes("admin")) return;
    link.setAttribute("href", applyQueryParams(link.getAttribute("href")));
});
