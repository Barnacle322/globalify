createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
    },
    watch: {
        asideMinified(value) {
            localStorage.setItem("asideMinified", value);
        },
    },
    mounted() {
        this.asideMinified = localStorage.getItem("asideMinified") === "true";

        this.loadMoreSearchHistories();
        this.setupInfiniteScroll();
    },
    methods: {
        setupInfiniteScroll() {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        this.loadMoreSearchHistories();
                    }
                });
            });
            observer.observe(this.$refs.historySentinel);
            this.observer = observer;
        },
        async loadMoreSearchHistories() {
            if (this.loading || this.noMoreItems) return;
            this.loading = true;
            try {
                const response = await fetch(`/search-history?page=${this.page}&limit=100`);
                if (!response.ok) {
                    throw new Error("Failed to fetch data");
                }

                const data = await response.json();
                if (data.length === 0) {
                    this.noMoreItems = true;
                    this.observer.disconnect();
                } else {
                    for (let item of data) {
                        if (!this.searchHistories.has(item.day)) {
                            this.searchHistories.set(item.day, item.histories);
                        } else {
                            this.searchHistories.get(item.day).push(...item.histories);
                        }
                    }
                    this.page++;
                }
            } catch (error) {
                console.error("Failed to fetch items:", error);
            } finally {
                this.loading = false;
            }
        },
        formatDate(day) {
            const date = new Date(day);
            const today = new Date();
            const yesterday = new Date();
            yesterday.setDate(today.getDate() - 1);

            const baseDate = date.toLocaleDateString("en-US", {
                weekday: "long",
                year: "numeric",
                month: "long",
                day: "numeric",
            });
            if (date.toDateString() === today.toDateString()) {
                return "Today" + " " + "-" + " " + baseDate;
            } else if (date.toDateString() === yesterday.toDateString()) {
                return "Yesterday" + " " + "-" + " " + baseDate;
            } else {
                return baseDate;
            }
        },
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            openAdvanced: false,

            searchHistories: new Map(),
            page: 1,
            loading: false,
            noMoreItems: false,
        };
    },
}).mount("#app");
