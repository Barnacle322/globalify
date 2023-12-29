window.onload = function () {
    const paramsArray = [
        "filter_field",
        "round",
        "industry",
        "sort_field",
        "descending",
        "rounds_exclusive",
        "industries_exclusive",
    ];
    paramsArray.forEach((param) => {
        setCheckedValuesFromParams(param);
    });
    setSearchValueFromParams();
    setSliderValuesFromParams("min_investment");
    setSliderValuesFromParams("max_investment");
};

function setCheckedValuesFromParams(inputName) {
    const urlParams = new URLSearchParams(window.location.search);
    const values = urlParams.getAll(inputName);

    values.forEach((value) => {
        const checkbox = document.querySelector(`input[name="${inputName}"][value="${value}"]`);
        if (checkbox) checkbox.checked = true;
    });
}

function setSliderValuesFromParams(sliderId) {
    const urlParams = new URLSearchParams(window.location.search);
    const value = urlParams.get(sliderId);

    if (value !== null) {
        const percentage = (value / 50000000) * 100;
        document.getElementById(sliderId).value = percentage;
    }
}

function setSearchValueFromParams() {
    const urlParams = new URLSearchParams(window.location.search);
    const value = urlParams.get("search");

    if (value !== null) {
        document.getElementById("search").value = value;
    }
}