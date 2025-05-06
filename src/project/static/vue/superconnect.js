const SessionRequestComponent = defineComponent({
    template: "#session-request-template",
    props: ["expertId"],
    mounted() {
        window.addEventListener("keydown", this.handleKeyDown);
        setTimeout(() => {
            document.addEventListener("click", this.handleOutsideClick);
        }, 0);
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        document.removeEventListener("click", this.handleOutsideClick);
    },
    methods: {
        async bookSession() {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/superconnect/book-session/${this.expertId}`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                console.log("Booking response:", response);
            } catch (error) {
                console.error("Error booking session:", error);
            }
        },
        closeSession() {
            this.$emit("close-session");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeSession();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeSession();
            }
        },
    },
    data() {
        return {};
    },
});

const FullExpertComponent = defineComponent({
    template: "#full-expert-template",
    props: ["expertId"],
    async mounted() {
        await this.fetchExpert(this.expertId);
        window.addEventListener("keydown", this.handleKeyDown);
        setTimeout(() => {
            document.addEventListener("click", this.handleOutsideClick);
        }, 0);
    },
    async created() {
        await this.fetchExpert(this.expertId);
        console.log("Expert data:", this.expert);
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        document.removeEventListener("click", this.handleOutsideClick);
    },
    methods: {
        async fetchExpert(expertId) {
            try {
                const response = await fetch(`/superconnect/expert/${expertId}`);
                if (!response.ok) {
                    throw new Error("Failed to fetch expert data");
                }
                const data = await response.json();
                this.expert = data.expert;
                console.log("Expert data:", this.expert.picture_url);
            } catch (error) {
                console.error("Error fetching expert data:", error);
            }
        },
        closeModal() {
            this.showModal = false;
        },
        closeExpert() {
            this.$emit("close-expert");
        },
        confirmBooking() {
            // Handle booking confirmation logic here
            console.log("Booking confirmed for:", this.selectedTimeslot);
            this.closeModal();
        },
        toggleExpansion() {
            this.isExpanded = !this.isExpanded;
        },
        formatDate(dateString) {
            if (!dateString) return null;
            const date = new Date(dateString);
            if (isNaN(date)) return dateString;
            return date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
        },
        getExperienceYears(qualifications) {
            if (!qualifications || !qualifications.length) return 0;

            // Find earliest start date
            let earliestDate = new Date();
            qualifications.forEach((qual) => {
                if (qual.start_date) {
                    const startDate = new Date(qual.start_date);
                    if (!isNaN(startDate) && startDate < earliestDate) {
                        earliestDate = startDate;
                    }
                }
            });

            // Calculate years of experience
            const now = new Date();
            const years = now.getFullYear() - earliestDate.getFullYear();
            return years > 0 ? years : "<1";
        },
        getQualificationColorClass(type) {
            const classes = {
                EDUCATION: "bg-gradient-to-b from-blue-500 to-indigo-600",
                WORK: "bg-gradient-to-b from-indigo-500 to-purple-600",
                CERTIFICATE: "bg-gradient-to-b from-green-500 to-teal-600",
                AWARD: "bg-gradient-to-b from-amber-500 to-orange-600",
                OTHER: "bg-gradient-to-b from-gray-500 to-slate-600",
            };

            return classes[type] || classes["OTHER"];
        },
        getCurrentPosition(positionId) {
            // Replace with your actual implementation to fetch position by ID
            // For now, return a placeholder
            return "Current Position";
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeExpert();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeExpert();
            }
        },
    },
    data() {
        return {
            selectedTimeslot: null,
            selectedDate: null,
            showModal: false,
            isLoading: false,
            isExpanded: false,
            expert: null,
        };
    },
});

createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
        FullExpertComponent,
        SessionRequestComponent,
    },
    watch: {
        asideMinified(value) {
            localStorage.setItem("asideMinified", value);
        },
    },
    mounted() {
        document.addEventListener("click", this.handleClickOutside);
        this.asideMinified = localStorage.getItem("asideMinified") == "true";
        this.loadExperts(1);
    },
    computed: {
        startPage() {
            return Math.max(1, this.pagination.page - 2);
        },
        endPage() {
            return Math.min(this.pagination.pages, this.pagination.page + 2);
        },
        pageNumbers() {
            const pages = [];
            for (let i = this.startPage; i <= this.endPage; i++) {
                if (i !== 1 && i !== this.pagination.pages) {
                    pages.push(i);
                }
            }
            return pages;
        },
    },
    methods: {
        async loadExperts(page) {
            this.loading = true;

            try {
                const queryParams = new URLSearchParams({
                    page: page,
                    per_page: this.pagination.per_page || 9,
                    expertise: this.filters.expertise,
                    region: this.filters.region,
                    search: this.filters.search,
                });

                const response = await fetch(`/superconnect/api/experts?${queryParams}`);
                if (!response.ok) {
                    throw new Error("Failed to fetch experts");
                }

                const data = await response.json();
                this.experts = data.experts;
                this.pagination = data.pagination;

                window.history.replaceState(null, "", `/superconnect/list?${queryParams.toString()}`);
            } catch (error) {
                console.error("Error loading experts:", error);
            } finally {
                this.loading = false;
            }
        },

        debouncedSearch() {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.loadExperts(1);
            }, 500);
        },
        setDefaultImage(event, name) {
            event.target.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=6366f1&color=fff&size=150`;
        },
        openExpert(expertId) {
            this.isFullExpertOpened = true;
            this.selectedExpertId = expertId;
        },
        openSessionRequest(expertId) {
            this.isSessionRequestOpened = true;
            this.selectedExpertId = expertId;
        },
    },
    data() {
        return {
            loading: false,
            experts: [],
            filters: {
                expertise: "All",
                region: "Worldwide",
                search: "",
            },
            pagination: {
                page: 1,
                per_page: 2,
                total: 0,
                pages: 0,
                has_next: false,
                has_prev: false,
                next_num: null,
                prev_num: null,
            },
            searchTimeout: null,
            timeslots: [],
            asideMinified: false,
            asideExpanded: true,
            selectedExpertId: null,
            isSessionRequestOpened: false,
            isFullExpertOpened: false,
        };
    },
}).mount("#app");
