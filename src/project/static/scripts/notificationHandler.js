function markNotificationAsRead(button) {
    const notificationId = button.getAttribute("data-notification-id");

    fetch(`/notification/edit/${notificationId}`).then((response) => {
        if (response.ok) {
            var notification = button.parentElement.parentElement;
            notification.classList.add("fade-out-down");
            var parent = notification.parentElement;
            var siblings = parent.children;

            // Parent element has a stack of children,
            // we need to apply the class slide down to all of the siblings
            // that are below(in the html structure) the notification we are removing

            // get the height of the notification we are removing
            const notificationHeight = notification.offsetHeight;

            for (let i = 0; i < siblings.length; i++) {
                if (siblings[i] === notification) {
                    for (let j = i + 1; j < siblings.length; j++) {
                        siblings[j].style = `transition: all 0.5s ease-in-out; transform: translateY(${
                            notificationHeight + 16
                        }px);`;
                    }
                }
            }
            setTimeout(() => {
                notification.remove();
                for (let i = 0; i < siblings.length; i++) {
                    siblings[i].style = "";
                }
            }, 500);
        } else {
            console.log("An error occurred while marking the notification as read.");
        }
    });
}
