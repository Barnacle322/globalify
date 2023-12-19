// When the page loads, check all checkboxes that are specified in the URL parameters
window.onload = function () {
    let paramsArray = [
        "filter_field",
        "round",
        "industry",
        "sort_field",
        "descending",
        "min_investment",
        "max_investment",
        "use_and_for_rounds",
        "use_and_for_industries",
    ];
    paramsArray.forEach((param) => {
        if (param === "min_investment" || param === "max_investment") {
            setSliderValuesFromParams(param);
        } else {
            setCheckedValuesFromParams(param);
        }
    });
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

// Get the values of slider with a given id
function getSliderValue(sliderId) {
    return document.getElementById(sliderId).value;
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

function setSliderValuesFromParams(sliderId) {
    let urlParams = new URLSearchParams(window.location.search);
    let value = urlParams.get(sliderId);

    if (value !== null) {
        document.getElementById(sliderId).value = value;
    }
}

// Perform a search based on the current form inputs
function search() {
    let searchQuery = document.getElementById("search").value;
    let roundValues = getCheckedValues("round");
    let industryValues = getCheckedValues("industry");
    let sortValues = getCheckedValues("sort_field");
    let descending = document.getElementById("descending").checked;
    let filterValues = getCheckedValues("filter_field");
    let minValue = getSliderValue("min_investment");
    let maxValue = getSliderValue("max_investment");
    let andRounds = document.getElementById("use_and_for_rounds").checked;
    let andIndustries = document.getElementById("use_and_for_industries").checked;
    console.log(andRounds)
    let paramsArray = getExistingParams([
        "q",
        "filter_field",
        "use_and_for_rounds",
        "use_and_for_industries",
        "round",
        "industry",
        "sort_field",
        "descending",
        "page",
        "min_investment",
        "max_investment",
    ]);

    roundValues.forEach((value) => paramsArray.push(`round=${encodeURIComponent(value)}`));
    industryValues.forEach((value) => paramsArray.push(`industry=${encodeURIComponent(value)}`));
    sortValues.forEach((value) => paramsArray.push(`sort_field=${encodeURIComponent(value)}`));
    filterValues.forEach((value) => paramsArray.push(`filter_field=${encodeURIComponent(value)}`));

    paramsArray.push(`min_investment=${encodeURIComponent(minValue)}`);
    paramsArray.push(`max_investment=${encodeURIComponent(maxValue)}`);

    if (andRounds) {
        paramsArray.push("use_and_for_rounds=1");
    } else {
        paramsArray.push("use_and_for_rounds=");
    }

    if (andIndustries) {
        paramsArray.push("use_and_for_industries=1");
    } else {
        paramsArray.push("use_and_for_industries=");
    }

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
