const menus = [
    { menu: "industry-options-menu", button: "industry-options" },
    { menu: "round-options-menu", button: "round-options" },
    { menu: "notable-investment-options-menu", button: "notable-investment-options" },
];

const showClasses = ["transform", "opacity-100", "scale-100"];
const hideClasses = ["opacity-0", "scale-95", "pointer-events-none"];

menus.forEach(({ menu, button }) => {
    const menuElement = document.getElementById(menu);
    const buttonElement = document.getElementById(button);

    if (!menuElement || !buttonElement) return;

    document.addEventListener("click", (event) => {
        if (!menuElement.contains(event.target) && !buttonElement.contains(event.target)) {
            menuElement.classList.remove(...showClasses);
            menuElement.classList.add(...hideClasses);
        }
    });

    buttonElement.onclick = () => {
        if (menuElement.classList.contains(hideClasses[0])) {
            menuElement.classList.add(...showClasses);
            menuElement.classList.remove(...hideClasses);
        } else {
            menuElement.classList.remove(...showClasses);
            menuElement.classList.add(...hideClasses);
        }
    };
});

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
