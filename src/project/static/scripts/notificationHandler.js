function markNotificationAsRead(button) {
    const notificationId = button.getAttribute('data-notification-id');
    const csrfToken = document.getElementById("csrf_token").value;

    fetch(`/notification/edit/${notificationId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
    })
    .then(response => {
        if (response.ok) {
            console.log('Notification marked as read');
            const notificationElement = button.closest('.fade-in-up');
            notificationElement.classList.add('fade-out-down');
            
            // Удаление элемента и обновление позиций после завершения анимации
            notificationElement.addEventListener('animationend', () => {
                notificationElement.remove();
                const notifications = document.querySelectorAll('.fade-in-up');
                notifications.forEach((notification, index) => {
                    notification.style.transition = 'bottom 0.5s ease'; // Установка плавной анимации движения вниз
                    notification.style.bottom = `${index * (notification.offsetHeight + 10)}px`; // Обновление позиций
                });
            });
        } else {
            console.error('Failed to mark notification as read');
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}
