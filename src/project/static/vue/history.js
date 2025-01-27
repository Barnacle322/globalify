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
        document.addEventListener("click", this.handleClickOutside);
        this.asideMinified = localStorage.getItem("asideMinified") == "true";
        this.searchType = new URLSearchParams(window.location.search).get("type") || "investor";

        this.setupInfiniteScroll();
        this.fetchHistoryTypes();
    },
    beforeUnmount() {
        document.removeEventListener("click", this.handleClickOutside);
        this.observer?.disconnect();
    },
    methods: {
        setupInfiniteScroll() {
            this.observer = new IntersectionObserver((entries) =>
                entries.forEach((entry) => {
                    if (entry.isIntersecting) this.loadMoreSearchHistories();
                }),
            );
            this.observer.observe(this.$refs.historySentinel);
        },
        async loadMoreSearchHistories() {
            if (this.loading || this.noMoreItems) return;
            this.loading = true;
            try {
                const params = new URLSearchParams();
                if (this.searchType) params.append("type", this.searchType);
                if (this.searchString) params.append("search", this.searchString);
                params.append("page", this.page);
                params.append("limit", 100);

                const response = await fetch(`/search-history?${params.toString()}`);

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
        selectType(typeValue) {
            this.dropdownOpened = false;
            this.searchType = typeValue;
            this.clearSelection();

            const url = new URL(window.location);
            url.searchParams.set("type", typeValue);
            window.history.pushState({}, "", url);

            this.page = 1;
            this.noMoreItems = false;
            this.searchHistories.clear();
            this.loadMoreSearchHistories();
        },
        handleClickOutside(event) {
            const dropdownContainer = this.$refs.dropdownContainer;
            if (dropdownContainer && !dropdownContainer.contains(event.target)) {
                this.dropdownOpened = false;
            }
        },
        async fetchHistoryTypes() {
            try {
                const response = await fetch("/history/types");
                if (!response.ok) throw new Error("Failed to fetch history types");
                this.historyTypes = await response.json();

                if (!this.historyTypes.some((t) => t.value === this.searchType)) {
                    this.searchType = this.historyTypes[0]?.value || "";
                }
            } catch (error) {
                console.error("Error fetching history types:", error);
            }
        },
        handleItemClick(event, item) {
            if (event.target.type === "checkbox") return;

            window.location.href = `/search${
                item.type === "investmentfirm" ? "/investment-firms" : item.type === "company" ? "/companies" : ""
            }?search=${item.query}`;
        },
        toggleSelection(itemId) {
            if (this.selectedItems.has(itemId)) {
                this.selectedItems.delete(itemId);
            } else {
                this.selectedItems.add(itemId);
            }
        },
        clearSelection() {
            this.selectedItems.clear();
        },

        async deleteSelected() {
            await this.deleteItems(Array.from(this.selectedItems));
        },

        async deleteItems(ids) {
            if (ids.length === 0) {
                console.warn("No items selected for deletion.");
                return;
            }

            try {
                const response = await fetch("/history/delete", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": document.getElementById("csrf_token").value,
                    },
                    body: JSON.stringify({ ids }),
                });

                if (!response.ok) throw new Error("Delete failed");

                ids.forEach((id) => this.removeHistoryItem(id));

                if (ids === Array.from(this.selectedItems)) {
                    this.selectedItems.clear();
                }
            } catch (error) {
                console.error("Delete error:", error);
            }
        },
        removeHistoryItem(id) {
            for (const [day, histories] of this.searchHistories) {
                const index = histories.findIndex((item) => item.id == id);
                if (index > -1) {
                    histories.splice(index, 1);
                    if (histories.length === 0) {
                        this.searchHistories.delete(day);
                    }
                    break;
                }
            }
        },
        handleSearch() {
            clearTimeout(this.debounceTimeout);
            this.debounceTimeout = setTimeout(() => {
                this.applySearch();
            }, 300);
        },
        applySearch() {
            this.page = 1;
            this.noMoreItems = false;
            this.searchHistories.clear();

            const url = new URL(window.location);
            if (this.searchString) {
                url.searchParams.set("search", this.searchString);
            } else {
                url.searchParams.delete("search");
            }
            window.history.pushState({}, "", url);

            this.loadMoreSearchHistories();
        },
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            openAdvanced: false,

            searchType: false,
            searchString: "",

            searchHistories: new Map(),
            page: 1,
            loading: false,
            noMoreItems: false,

            historyTypes: [],
            observer: null,
            dropdownOpened: false,
            selectedItems: new Set(),
            debounceTimeout: null,
        };
    },
}).mount("#app");
