document.getElementById("search").addEventListener("keydown", function (event) {
    if (event.key === "Enter") search();
});

function search() {
    const roundValues = getCheckedValues("round");
    const industryValues = getCheckedValues("industry");
    const sortValues = getCheckedValues("sort_field");
    const filterValues = getCheckedValues("filter_field");

    const searchQuery = document.getElementById("search").value;
    const minValue = document.getElementById("min_investment").value;
    const maxValue = document.getElementById("max_investment").value;

    const descending = document.getElementById("descending").checked;
    const roundsExclusive = document.getElementById("rounds_exclusive").checked;
    const industriesExclusive = document.getElementById("industries_exclusive").checked;

    const paramsArray = getExistingParams([
        "q",
        "filter_field",
        "rounds_exclusive",
        "industries_exclusive",
        "round",
        "industry",
        "sort_field",
        "descending",
        "page",
        "min_investment",
        "max_investment",
    ]);

    handleLists(roundValues, "round", paramsArray);
    handleLists(industryValues, "industry", paramsArray);
    handleLists(sortValues, "sort_field", paramsArray);
    handleLists(filterValues, "filter_field", paramsArray);

    handleInvestmentRange(minValue, "min_investment", paramsArray);
    handleInvestmentRange(maxValue, "max_investment", paramsArray);

    handleBooleans(roundsExclusive, "rounds_exclusive", paramsArray);
    handleBooleans(industriesExclusive, "industries_exclusive", paramsArray);
    handleBooleans(descending, "descending", paramsArray);

    if (searchQuery !== "") paramsArray.unshift(`q=${encodeURIComponent(searchQuery)}`);

    addParamsToUrl(paramsArray);
}

function getCheckedValues(inputName) {
    const checkboxes = document.querySelectorAll(`input[name="${inputName}"]:checked`);
    return Array.from(checkboxes).map((checkbox) => checkbox.value);
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

function handleLists(values, paramName, paramsArray) {
    values.forEach((value) => paramsArray.push(`${paramName}=${encodeURIComponent(value)}`));
}

function handleInvestmentRange(value, paramName, paramsArray) {
    if (value == 0 || value == 100) return;
    if (value !== "") {
        const actualValue = Math.floor((value / 100) * 50000000);
        paramsArray.push(`${paramName}=${encodeURIComponent(actualValue)}`);
    }
}

function handleBooleans(value, paramName, paramsArray) {
    if (value) {
        paramsArray.push(`${paramName}=${value ? 1 : ""}`);
    }
}

function addParamsToUrl(paramsArray) {
    const paramsString = paramsArray.length > 0 ? "?" + paramsArray.join("&") : "";
    const baseUrl = window.location.href.split("?")[0];
    const newUrl = baseUrl + paramsString;

    window.location.href = newUrl;
}

const lowerSlider = document.getElementById("min_investment");
const upperSlider = document.getElementById("max_investment");

lowerSlider.oninput = function () {
    if (parseInt(lowerSlider.value) >= parseInt(upperSlider.value)) {
        lowerSlider.value = parseInt(upperSlider.value) - 1;
    }
};

upperSlider.oninput = function () {
    if (parseInt(upperSlider.value) <= parseInt(lowerSlider.value)) {
        upperSlider.value = parseInt(lowerSlider.value) + 1;
    }
};

document.addEventListener('DOMContentLoaded', function () {
    function handleButton(buttonId, optionsId, checkboxName) {
        var checkboxes = document.querySelectorAll(`#${optionsId} input[type="checkbox"]`);
        var button = document.getElementById(buttonId);

        function updateButtonBorderColor() {
            var anyChecked = Array.from(checkboxes).some(function (cb) {
                return cb.checked;
            });

            button.style.borderColor = anyChecked ? 'rgb(14 165 233 / var(--tw-bg-opacity))' : 'rgb(226 232 240 / var(--tw-border-opacity))';
        }

        checkboxes.forEach(function (checkbox) {
            checkbox.addEventListener('change', function () {
                updateButtonBorderColor();
                localStorage.setItem(`${checkboxName}CheckboxStates`, JSON.stringify(Array.from(checkboxes).map(cb => cb.checked)));
            });
        });

        var savedCheckboxStates = localStorage.getItem(`${checkboxName}CheckboxStates`);
        if (savedCheckboxStates) {
            savedCheckboxStates = JSON.parse(savedCheckboxStates);
            checkboxes.forEach(function (checkbox, index) {
                checkbox.checked = savedCheckboxStates[index];
            });
            updateButtonBorderColor();
        }
    }

    handleButton('filter-options-menu', 'filter-options', 'filter_field');

    handleButton('round-options-menu', 'round-options', 'round');

    handleButton('industry-options-menu', 'industry-options', 'industry');

    handleButton('sorting-options-menu', 'sorting-options', 'sort_field');
});