document.addEventListener("DOMContentLoaded", () => {
    const closeMessage = () => {
        const toastSuccess = document.getElementById("bottom-right-message");
        if (toastSuccess) {
            toastSuccess.classList.add("fade-out-right");
            setTimeout(() => {
                toastSuccess.remove();
                clearUrlParams();
            }, 1000);
        }
    };

    const clearUrlParams = () => {
        const newUrl = `${window.location.protocol}//${window.location.host}${window.location.pathname}`;
        window.history.replaceState({ path: newUrl }, "", newUrl);
    };

    const closeButton = document.querySelector("#bottom-right-message button");
    if (closeButton) {
        closeButton.addEventListener("click", closeMessage);
    }

    setTimeout(closeMessage, 3000);
});
