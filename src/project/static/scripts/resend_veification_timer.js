function startResendTimer(event) {
    var timerElement = document.getElementById("resendTimer");
    var resendButton = document.getElementById("resendButton");

    var countdown = 15;

    timerElement.innerText = "Resend available in " + countdown + " seconds";
    timerElement.style.display = "inline-block";
    resendButton.style.display = "none";

    var interval = setInterval(function () {
        countdown--;
        if (countdown <= 0) {
            clearInterval(interval);
            timerElement.style.display = "none";
            resendButton.style.display = "inline-block";
        } else {
            timerElement.innerText = "Resend available in " + countdown + " seconds";
        }
    }, 1000);
    event;
}
