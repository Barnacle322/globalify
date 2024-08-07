const { defineComponent, createApp } = Vue;

const NotificationComponent = defineComponent({
    template: "#notifications-template",
    emits: ["all-notifications-read", "closenotifications"],
    data() {
        return {
            notifications: [],
            inboxNotifications: [],
            selectedTab: "inbox",
            observer: null,
            loading: false,
            reachedEnd: false,
            page: 2,
        };
    },
    watch: {
        selectedTab(newVal, oldVal) {
            if (newVal === oldVal) {
                return;
            }

            if (newVal === "inbox") {
                this.$refs.inbox.setAttribute("data-selected", "true");
                this.$refs.archive.setAttribute("data-selected", "false");
                this.page = 2;
                this.setupInfinteScroll();
            } else {
                this.$refs.inbox.setAttribute("data-selected", "false");
                this.$refs.archive.setAttribute("data-selected", "true");
                this.page = 2;
                this.setupInfinteScroll();
            }
        },
    },
    methods: {
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.$emit("closenotifications");
            }
        },
        timeDifference(current, previous) {
            let msPerMinute = 60 * 1000;
            let msPerHour = msPerMinute * 60;
            let msPerDay = msPerHour * 24;
            let msPerMonth = msPerDay * 30;
            let msPerYear = msPerDay * 365;

            let elapsed = current - previous;

            if (elapsed < msPerMinute) {
                const seconds = Math.round(elapsed / 1000);
                return seconds + (seconds === 1 ? " second ago" : " seconds ago");
            } else if (elapsed < msPerHour) {
                const minutes = Math.round(elapsed / msPerMinute);
                return minutes + (minutes === 1 ? " minute ago" : " minutes ago");
            } else if (elapsed < msPerDay) {
                const hours = Math.round(elapsed / msPerHour);
                return hours + (hours === 1 ? " hour ago" : " hours ago");
            } else if (elapsed < msPerMonth) {
                const days = Math.round(elapsed / msPerDay);
                return days + (days === 1 ? " day ago" : " days ago");
            } else if (elapsed < msPerYear) {
                const months = Math.round(elapsed / msPerMonth);
                return months + (months === 1 ? " month ago" : " months ago");
            } else {
                const years = Math.round(elapsed / msPerYear);
                return years + (years === 1 ? " year ago" : " years ago");
            }
        },
        async setupInfinteScroll() {
            if (this.selectedTab === "inbox") {
                const response = await fetch("/notifications");
                if (response.ok) {
                    const data = await response.json();
                    this.notifications = data.notifications.filter((notification) => !notification.is_read);
                }
            } else if (this.selectedTab === "archive") {
                const response = await fetch("/notifications/archived");
                if (response.ok) {
                    const data = await response.json();
                    this.notifications = data.notifications.map((notification) => notification);
                }
            }
            const options = {
                root: null,
                rootMargin: "0px",
                threshold: 0.5,
            };
            const sentinel = document.getElementById("notification-sentinel");
            this.observer = new IntersectionObserver((entries, observer) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        this.reachedEnd = true;
                        this.loadMoreNotifications();
                    }
                });
            }, options);
            this.observer.observe(sentinel);
        },
        async loadMoreNotifications() {
            if (this.loading) return;
            if (!this.loading && this.reachedEnd) {
                this.loading = true;
                try {
                    let response;
                    if (this.selectedTab === "inbox") {
                        response = await fetch(`/notifications?page=${this.page}`);
                    } else if (this.selectedTab === "archive") {
                        response = await fetch(`/notifications/archived?page=${this.page}`);
                    }

                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    if (response.ok) {
                        const data = await response.json();
                        this.notifications.push(...data.notifications);
                        this.page++;
                    } else {
                        console.error("Error fetching notifications:", response.statusText);
                    }
                } catch (error) {
                    console.error("Error fetching notifications:", error.message);
                } finally {
                    this.loading = false;
                }
            }
        },
        async markAllAsRead() {
            try {
                const csrfToken = document.getElementById("csrf_token").value;
                const response = await fetch("/notifications/mark-all-read", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                console.log(response);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                this.notifications.forEach((notification) => {
                    notification.is_read = true;
                });
                this.notifications = [];
                this.inboxNotifications = [];
                this.$emit("all-notifications-read");
            } catch (e) {
                console.error("Error marking all notifications as read:", e);
            }
        },
        async markAsRead(notificationId) {
            try {
                const csrfToken = document.getElementById("csrf_token").value;
                const response = await fetch(`/notification/mark-read/${notificationId}`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                this.notifications = this.notifications.filter((notification) => notification.id !== notificationId);
                this.inboxNotifications = this.inboxNotifications.filter(
                    (notification) => notification.id !== notificationId,
                );
            } catch (e) {
                console.error("Error marking notification as read:", e);
            }
        },
    },
    async mounted() {
        await this.setupInfinteScroll();
    },
    beforeUnmount() {
        this.observer.disconnect();
        window.removeEventListener("keydown", this.handleKeyDown);
    },
});

const AsideComponent = defineComponent({
    props: ["place", "minified"],
    template: "#aside-template",
    data() {
        return {
            currentPath: null,
        };
    },
    mounted() {
        this.currentPath = window.location.pathname.split("/")[1];
        if (["suggestions", "investor", "investment-firm"].includes(this.currentPath)) {
            this.currentPath = "search";
        }
    },
});

const AsideMobileComponent = defineComponent({
    template: "#aside-mobile-template",
    methods: {
        closeAside() {
            this.$emit("close-aside");
        },
    },
    data() {
        return {
            currentPath: null,
        };
    },
    mounted() {
        this.currentPath = window.location.pathname.split("/")[1];
    },
});

const Bookmark = defineComponent({
    template: "#bookmark-template",
    emits: ["bookmarked", "closebookmarks"],
    data() {
        return {
            bookmarks: [],
            openedDropdownId: null,
            selectedTab: "investor",
            observer: null,
            loading: false,
            reachedEnd: false,
            page: 2,
        };
    },
    watch: {
        selectedTab(newVal, oldVal) {
            if (newVal === oldVal) {
                return;
            }

            if (newVal === "investor") {
                this.$refs.investor.setAttribute("data-selected", "true");
                this.$refs.investment_firm.setAttribute("data-selected", "false");
                this.page = 2;
                this.setupInfinteScroll();
            } else {
                this.$refs.investor.setAttribute("data-selected", "false");
                this.$refs.investment_firm.setAttribute("data-selected", "true");
                this.page = 2;
                this.setupInfinteScroll();
            }
        },
    },
    methods: {
        formatDate(date) {
            const options = { year: "numeric", month: "long", day: "numeric" };
            return new Date(date).toLocaleString("en-US", options);
        },
        async closeBookmark(event) {
            this.$nextTick(() => {
                if (!this.$refs.removebookmark.$el.contains(event.target)) {
                    this.bookmarksOpened = false;
                }
            });
        },
        async setupInfinteScroll() {
            if (this.selectedTab === "investor") {
                const response = await fetch("/investors/bookmarks");
                if (response.ok) {
                    data = await response.json();
                    this.bookmarks = data.bookmarks;
                }
            } else if (this.selectedTab === "investment_firm") {
                const response = await fetch("/investment-firms/bookmarks");
                data = await response.json();
                if (response.ok) {
                    this.bookmarks = data.bookmarks;
                }
            }
            const options = {
                root: null,
                rootMargin: "0px",
                threshold: 0.5,
            };

            const sentinel = document.getElementById("bookmark-sentinel");
            this.observer = new IntersectionObserver((entries, observer) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        this.reachedEnd = true;
                        this.loadMoreBookmarks();
                    }
                });
            }, options);
            this.observer.observe(sentinel);
        },
        async loadMoreBookmarks() {
            if (this.loading) return;
            if (!this.loading && this.reachedEnd) {
                this.loading = true;
                try {
                    let response;
                    if (this.selectedTab === "investor") {
                        response = await fetch(`/investors/bookmarks?page=${this.page}`);
                    } else if (this.selectedTab === "investment_firm") {
                        response = await fetch(`/investment-firms/bookmarks?page=${this.page}`);
                    }

                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    if (response.ok) {
                        const data = await response.json();

                        this.bookmarks.push(...data.bookmarks);
                        this.page++;
                    } else {
                        console.error("Error fetching bookmarks:", response.statusText);
                    }
                } catch (error) {
                    console.error("Error fetching bookmarks:", error.message);
                } finally {
                    this.loading = false;
                }
            }
        },

        async unbookmarkInvestor(investorId) {
            try {
                const csrfToken = document.getElementById("csrf_token").value;
                const response = await fetch(`/investor/${investorId}/bookmark`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });

                if (response.ok) {
                    this.bookmarks = this.bookmarks.filter((investor) => investor.id !== investorId);

                    this.$emit("bookmarked", { investorId: investorId, status: false });
                } else {
                    console.error("Error removing bookmark:", response.statusText);
                }
            } catch (error) {
                console.error("Error removing bookmark:", error.message);
            }
        },

        async UnbookmarkInvestmentFirm(firmId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/investment-firm/${firmId}/bookmark`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });

                if (response.ok) {
                    this.bookmarks = this.bookmarks.filter((firm) => firm.id !== firmId);
                } else {
                    console.error("Error removing bookmark:", response.statusText);
                }
            } catch (error) {
                console.error("Error removing bookmark:", error.message);
            }
        },
        computedHref(data) {
            if (this.selectedTab === "investor") {
                return "/investor/" + data.slug;
            } else if (this.selectedTab === "investment_firm") {
                return "/investment-firm/" + data.slug;
            } else {
                return "#";
            }
        },
        getTwitterHandle(url) {
            return url.split("/").pop();
        },
    },
    async mounted() {
        await this.setupInfinteScroll();
        window.addEventListener("click", this.closeRemoveBookmark);
    },
    beforeUnmount() {
        this.observer.disconnect();
        window.removeEventListener("click", this.closeRemoveBookmark);
    },
});

const NavbarComponent = defineComponent({
    template: "#navbar-template",
    emits: ["open-aside", "open-notifications"],
    components: {
        Bookmark,
        NotificationComponent,
    },
    data() {
        return {
            bookmarksOpened: false,
            ignoreNextOutsideClickBookmarks: false,
            notificationsOpened: false,
            ignoreNextOutsideClickNotifications: false,
            notifications: [],
        };
    },
    methods: {
        expandAside() {
            this.$emit("open-aside");
        },
        openBookmark() {
            this.bookmarksOpened = true;
            this.ignoreNextOutsideClickBookmarks = true;
        },
        closeBookmark(event) {
            if (this.ignoreNextOutsideClickBookmarks) {
                this.ignoreNextOutsideClickBookmarks = false;
                return;
            } else if (event && this.$refs.bookmark && !this.$refs.bookmark.$el.contains(event.target)) {
                this.bookmarksOpened = false;
            }
        },
        openNotifications() {
            this.notificationsOpened = true;
            this.ignoreNextOutsideClickNotifications = true;
        },
        closeNotifications(event) {
            if (this.ignoreNextOutsideClickNotifications) {
                this.ignoreNextOutsideClickNotifications = false;
                return;
            } else if (event && this.$refs.notifications && !this.$refs.notifications.$el.contains(event.target)) {
                this.notificationsOpened = false;
            }
        },
        async fetchNotificationInbox() {
            try {
                const response = await fetch("/notifications");
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                this.notifications = data.notifications.map((notification) => notification);
            } catch (e) {
                console.error("Error fetching notifications:", e);
            }
        },
        handleAllNotificationsRead() {
            this.notifications.forEach((notification) => {
                notification.is_read = true;
            });
        },
        startPolling() {
            this.pollingInterval = setInterval(async () => {
                await this.fetchNotificationInbox();
            }, 15000);
        },
        stopPolling() {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        },
        handleVisibilityChange() {
            if (document.hidden) {
                this.stopPolling();
            } else {
                this.startPolling();
            }
        },
    },
    computed: {
        unreadNotifications() {
            return this.notifications.some((notification) => !notification.is_read);
        },
    },
    async mounted() {
        window.addEventListener("click", this.closeBookmark);
        window.addEventListener("click", this.closeNotifications);
        await this.fetchNotificationInbox();
        if (!document.hidden) {
            this.startPolling();
        }
        document.addEventListener("visibilitychange", this.handleVisibilityChange);
    },
    beforeUnmount() {
        window.removeEventListener("click", this.closeBookmark);
        window.removeEventListener("click", this.closeNotifications);
        window.removeEventListener("keydown", this.handleKeyDown);
        document.removeEventListener("visibilitychange", this.handleVisibilityChange);
    },
});
