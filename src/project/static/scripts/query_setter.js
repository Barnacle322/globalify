let openAdvanced = false;

window.onload = function () {
    const paramsArray = [
        "filter_field",
        "round",
        "industry",
        "sort_field",
        "descending",
        "rounds_exclusive",
        "industries_exclusive",
        "country",
    ];
    paramsArray.forEach((param) => {
        setCheckedValuesFromParams(param);
    });
    setSearchValueFromParams();
    setSliderValuesFromParams("min_investment");
    setSliderValuesFromParams("max_investment");
    if (openAdvanced) toggleAdvanced();
};

function setCheckedValuesFromParams(inputName) {
    const urlParams = new URLSearchParams(window.location.search);
    const values = urlParams.getAll(inputName);

    values.forEach((value) => {
        openAdvanced = true;
        const checkbox = document.querySelector(`input[name="${inputName}"][value="${value}"]`);
        if (checkbox) checkbox.checked = true;
    });
}

function setSliderValuesFromParams(sliderId) {
    const urlParams = new URLSearchParams(window.location.search);
    const value = urlParams.get(sliderId);

    if (value !== null) {
        openAdvanced = true;
        const percentage = (value / 50000000) * 100;
        document.getElementById(sliderId).value = percentage;
    }
}

function setSearchValueFromParams() {
    const urlParams = new URLSearchParams(window.location.search);
    const value = urlParams.get("search");

    if (value !== null) {
        openAdvanced = true;
        document.getElementById("search").value = value;
    }
}

function toggleAdvanced() {
    const advancedMenu = document.getElementById("advanced-menu");

    const openedAdvanced = document.getElementById("opened-advanced");
    const closedAdvanced = document.getElementById("closed-advanced");

    if (advancedMenu.classList.contains("hidden")) {
        advancedMenu.classList.remove("hidden");
        advancedMenu.classList.add("flex");

        openedAdvanced.classList.remove("hidden");
        closedAdvanced.classList.add("hidden");
    } else {
        advancedMenu.classList.add("hidden");
        advancedMenu.classList.remove("flex");

        openedAdvanced.classList.add("hidden");
        closedAdvanced.classList.remove("hidden");
    }
}
