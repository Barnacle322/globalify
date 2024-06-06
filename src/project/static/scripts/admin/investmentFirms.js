async function deleteInvestmentFirm(id) {
    const csrfToken = document.getElementById("csrf_token").value;

    if (!confirm("Are you sure you want to delete this investment firm?")) {
        return;
    }

    const response = await fetch(`/admin/investment-firm/${id}/delete`, {
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
