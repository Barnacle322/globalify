function enableButton() {
    document.getElementById("saveButton").disabled = false;
}

async function updateInvestmentFirm() {
    const csrfToken = document.getElementById("csrf_token").value;

    const name = document.getElementById("name").value;
    const about = document.getElementById("about").value;
    const website = document.getElementById("website").value;
    const email = document.getElementById("email").value;
    const phone_number = document.getElementById("phone_number").value;
    const n_investments = document.getElementById("n_investments").value;
    const n_exits = document.getElementById("n_exits").value;
    const n_employees = document.getElementById("n_employees").value;
    const min_investment = document.getElementById("min_investment").value;
    const max_investment = document.getElementById("max_investment").value;
    const location = document.getElementById("location").value;
    const selectedRounds = Array.from(document.querySelectorAll('input[name="selected_rounds"]:checked')).map((input) =>
        parseInt(input.value, 10),
    );
    const selectedIndustries = Array.from(document.querySelectorAll('input[name="selected_industries"]:checked')).map(
        (input) => parseInt(input.value, 10),
    );
    const selectedNotableInvestments = Array.from(
        document.querySelectorAll('input[name="selected_notable_investments"]:checked'),
    ).map((input) => parseInt(input.value, 10));

    const dataString = JSON.stringify({
        name: name,
        about: about,
        website: website,
        email: email,
        phone_number: phone_number,
        n_investments: n_investments,
        n_exits: n_exits,
        n_employees: n_employees,
        min_investment: min_investment,
        max_investment: max_investment,
        location: location,
        round: selectedRounds,
        industry: selectedIndustries,
        notable_investment: selectedNotableInvestments,
    });

    try {
        const response = await fetch("", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
            body: dataString,
        });
        if (response.redirected) {
            window.location.href = response.url;
        }
    } catch (error) {
        console.error("Error:", error);
    }
}

async function deleteInvestmentFirm(id) {
    const csrfToken = document.getElementById("csrf_token").value;

    if (!confirm("Are you sure you want to delete this investment firm?")) {
        return;
    }

    const response = await fetch(`/admin/dashboard/investment-firm/${id}/delete`, {
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

async function createInvestmentFirm() {
    const csrf_token = document.getElementById("csrf_token").value;

    const name = document.getElementById("name").value;
    const about = document.getElementById("about").value;
    const website = document.getElementById("website").value;
    const email = document.getElementById("email").value;
    const phone_number = document.getElementById("phone_number").value;
    const n_investments = document.getElementById("n_investments").value;
    const n_exits = document.getElementById("n_exits").value;
    const n_employees = document.getElementById("n_employees").value;
    const min_investment = document.getElementById("min_investment").value;
    const max_investment = document.getElementById("max_investment").value;
    const location = document.getElementById("location").value;

    let roundCheckboxes = document.querySelectorAll('input[name="selected_rounds"]:checked');
    const selectedRounds = Array.from(roundCheckboxes).map((checkbox) => checkbox.parentElement.textContent.trim());

    let industryCheckboxes = document.querySelectorAll('input[name="selected_industries"]:checked');
    const selectedIndustries = Array.from(industryCheckboxes).map((checkbox) =>
        checkbox.parentElement.textContent.trim(),
    );

    let notableInvestmentsCheckboxes = document.querySelectorAll('input[name="selected_notable_investments"]:checked');
    const selectedNotableInvestments = Array.from(notableInvestmentsCheckboxes).map((checkbox) =>
        checkbox.parentElement.textContent.trim(),
    );

    const dataString = JSON.stringify({
        name: name,
        about: about,
        website: website,
        email: email,
        phone_number: phone_number,
        n_investments: n_investments,
        n_exits: n_exits,
        n_employees: n_employees,
        min_investment: min_investment,
        max_investment: max_investment,
        location: location,
        round: selectedRounds,
        industry: selectedIndustries,
        notable_investment: selectedNotableInvestments,
    });

    try {
        const response = await fetch("/admin/investment-firm/create", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrf_token,
            },
            body: dataString,
        });
        if (response.redirected) {
            window.location.href = response.url;
        }
    } catch (error) {
        console.error("Error:", error);
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
