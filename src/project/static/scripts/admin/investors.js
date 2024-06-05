function deleteInvestor(id) {
    const csrfToken = document.getElementById("csrf_token").value;

    if (!confirm("Are you sure you want to delete this investor?")) {
        return;
    }

    const response = fetch(`/admin/dashboard/investor/${id}/delete`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
        },
    });
    if (response.ok) {
        window.location.reload();
    }
}

document.getElementById("search-btn").addEventListener("click", function (event) {
    search();
});

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
    return new URLSearchParams(window.location.search);
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
