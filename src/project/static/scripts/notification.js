document.addEventListener('DOMContentLoaded', function () {
    var closeButton = document.querySelector('#toast-success button');
    var toastSuccess = document.getElementById('toast-success');

    closeButton.addEventListener('click', function () {
        toastSuccess.classList.add('fade-out', 'fixed-notification');

        setTimeout(function () {
            toastSuccess.style.display = 'none';
        }, 500);
        var currentUrl = window.location.href;

        if (currentUrl.includes('notification')) {
            var updatedUrl = currentUrl.split('?')[0];
            window.history.replaceState({}, document.title, updatedUrl);
        }
    });
});