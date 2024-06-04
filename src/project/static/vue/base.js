const { defineComponent, createApp } = Vue;

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
        console.log(this.currentPath);
        if (["suggestions", "investor"].includes(this.currentPath)) {
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
    emits: ["open-aside"],
    components: {
        Bookmark,
    },
    data() {
        return {
            bookmarksOpened: false,
            ignoreNextOutsideClickBookmarks: false,
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
        handleAllNotificationsRead() {
            this.notifications.forEach((notification) => {
                notification.is_read = true;
            });
        },
    },
    async mounted() {
        window.addEventListener("click", this.closeBookmark);
    },
    beforeUnmount() {
        window.removeEventListener("click", this.closeBookmark);
    },
});
