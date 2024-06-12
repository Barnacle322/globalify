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

document.getElementById("searchInput").addEventListener("input", function () {
    var searchInput = this.value;
    if (searchInput.length > 1) {
        fetch(`/admin/search_users/${searchInput}`)
            .then((response) => response.json())
            .then((data) => {
                var userList = document.getElementById("userList");
                userList.innerHTML = "";
                data.users.forEach((email) => {
                    var li = document.createElement("li");
                    li.textContent = email;
                    li.style.cursor = "pointer";
                    li.addEventListener("click", function () {
                        document.getElementById("searchInput").value = this.textContent;
                        userList.innerHTML = "";
                    });
                    userList.appendChild(li);
                });
            })
            .catch((error) => console.error("Error searching users:", error));
    } else {
        document.getElementById("userList").innerHTML = "";
    }
});

async function updateInvestor() {
    const csrfToken = document.getElementById("csrf_token").value;

    const selectedRounds = Array.from(document.querySelectorAll('input[name="selected_rounds"]:checked')).map((input) =>
        parseInt(input.value, 10),
    );
    const selectedIndustries = Array.from(document.querySelectorAll('input[name="selected_industries"]:checked')).map(
        (input) => parseInt(input.value, 10),
    );
    const selectedNotableInvestments = Array.from(
        document.querySelectorAll('input[name="selected_notable_investments"]:checked'),
    ).map((input) => parseInt(input.value, 10));

    let dataString = JSON.stringify({
        first_name: document.getElementById("first_name").value,
        last_name: document.getElementById("last_name").value,
        slug: document.getElementById("slug").value,
        firm_name: document.getElementById("firm_name").value,
        position: document.getElementById("position").value,
        about: (about = document.getElementById("about").value),
        website: document.getElementById("website").value,
        linkedin: document.getElementById("linkedin").value,
        twitter: document.getElementById("twitter").value,
        email: document.getElementById("email").value,
        phone_number: document.getElementById("phone_number").value,
        n_investments: document.getElementById("n_investments").value,
        n_exits: document.getElementById("n_exits").value,
        min_investment: document.getElementById("min_investment").value,
        max_investment: document.getElementById("max_investment").value,
        location: document.getElementById("location").value,
        user_email: document.getElementById("searchInput").value,
        rounds: selectedRounds,
        industries: selectedIndustries,
        notable_investments: selectedNotableInvestments,
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

async function createInvestor() {
    const csrf_token = document.getElementById("csrf_token").value;

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

    let dataString = JSON.stringify({
        first_name: document.getElementById("first_name").value,
        last_name: document.getElementById("last_name").value,
        slug: document.getElementById("slug").value,
        firm_name: document.getElementById("firm_name").value,
        position: document.getElementById("position").value,
        about: (about = document.getElementById("about").value),
        website: document.getElementById("website").value,
        linkedin: document.getElementById("linkedin").value,
        twitter: document.getElementById("twitter").value,
        email: document.getElementById("email").value,
        phone_number: document.getElementById("phone_number").value,
        n_investments: document.getElementById("n_investments").value,
        n_exits: document.getElementById("n_exits").value,
        min_investment: document.getElementById("min_investment").value,
        max_investment: document.getElementById("max_investment").value,
        location: document.getElementById("location").value,
        user_email: document.getElementById("searchInput").value,
        rounds: selectedRounds,
        industries: selectedIndustries,
        notable_investments: selectedNotableInvestments,
    });

    try {
        const response = await fetch("", {
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
