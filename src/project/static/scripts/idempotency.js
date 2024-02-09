const forms = document.querySelectorAll("form");

forms.forEach((form) => {
    const submitButton = form.querySelector("button[type='submit']");

    form.addEventListener("submit", function (event) {
        submitButton.disabled = true;
        submitButton.innerText = "Loading...";
        submitButton.classList.add("opacity-50", "cursor-not-allowed");
    });
});
