// When the page loads, check all checkboxes that are specified in the URL parameters
window.onload = function () {
    let paramsArray = ["filter_field", "round", "industry", "sort_field", "descending"];
    paramsArray.forEach((param) => setCheckedValuesFromParams(param));
};

// When the Enter key is pressed in the search input, perform a search
let searchInput = document.getElementById("search");
searchInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        search();
    }
});

// Get the values of all checked checkboxes with a given name
function getCheckedValues(inputName) {
    let checkboxes = document.querySelectorAll(`input[name="${inputName}"]:checked`);
    let values = Array.from(checkboxes).map((checkbox) => checkbox.value);
    return values;
}

// Get all URL parameters except for those specified
function getExistingParams(excludedParams) {
    let urlParams = new URLSearchParams(window.location.search);
    let paramsArray = [];

    for (let param of urlParams) {
        if (!excludedParams.includes(param[0])) {
            paramsArray.push(`${param[0]}=${encodeURIComponent(param[1])}`);
        }
    }

    return paramsArray;
}

// Add an array of parameters to the current URL
function addParamsToUrl(paramsArray) {
    let paramsString = paramsArray.length > 0 ? "?" + paramsArray.join("&") : "";
    let baseUrl = window.location.href.split("?")[0];
    let newUrl = baseUrl + paramsString;

    window.location.href = newUrl;
}

// Check all checkboxes that are specified in the URL parameters
function setCheckedValuesFromParams(inputName) {
    let urlParams = new URLSearchParams(window.location.search);
    let values = urlParams.getAll(inputName);

    values.forEach((value) => {
        let checkbox = document.querySelector(`input[name="${inputName}"][value="${value}"]`);
        if (checkbox) {
            checkbox.checked = true;
        }
    });
}

// Perform a search based on the current form inputs
function search() {
    let searchQuery = document.getElementById("search").value;
    let roundValues = getCheckedValues("round");
    let industryValues = getCheckedValues("industry");
    let sortValues = getCheckedValues("sort_field");
    let descending = document.getElementById("descending").checked;
    let filterValues = getCheckedValues("filter_field");

    let paramsArray = getExistingParams(["q", "filter_field", "round", "industry", "sort_field", "descending"]);

    roundValues.forEach((value) => paramsArray.push(`round=${encodeURIComponent(value)}`));
    industryValues.forEach((value) => paramsArray.push(`industry=${encodeURIComponent(value)}`));
    sortValues.forEach((value) => paramsArray.push(`sort_field=${encodeURIComponent(value)}`));
    filterValues.forEach((value) => paramsArray.push(`filter_field=${encodeURIComponent(value)}`));

    if (descending) {
        paramsArray.push("descending=1");
    } else {
        paramsArray.push("descending=");
    }

    if (searchQuery !== "") {
        paramsArray.unshift(`q=${encodeURIComponent(searchQuery)}`);
    }

    addParamsToUrl(paramsArray);
}
