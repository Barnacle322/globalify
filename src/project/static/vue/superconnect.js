const SessionRequestComponent = defineComponent({
    template: "#session-request-template",
    props: ["expertId"],
    async mounted() {
        window.addEventListener("keydown", this.handleKeyDown);
        setTimeout(() => {
            document.addEventListener("click", this.handleOutsideClick);
        }, 0);
        await this.fetchExpert(this.expertId);
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        document.removeEventListener("click", this.handleOutsideClick);
    },
    methods: {
        async requestSession() {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/expert/book-session/${this.expertId}`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify({
                        expert_id: this.expertId,
                        notes: this.notes,
                    }),
                });
                const data = await response.json();

                if (data.error) {
                    this.errorMessage = data.error;
                    return;
                }

                console.log("Session booking result:", data);

                if (data.success) {
                    // Перенаправляем на Stripe Checkout
                    window.location.href = data.invoice_url;
                } else {
                    this.errorMessage = data.error || "Failed to create checkout session";
                }
            } catch (error) {
                console.error("Error booking session:", error);
            }
        },
        async fetchExpert(expertId) {
            try {
                const response = await fetch(`/expert/get/${expertId}`);
                if (!response.ok) {
                    throw new Error("Failed to fetch expert data");
                }
                const data = await response.json();
                this.expert = data.expert;
                console.log("Expert data:", this.expert);
            } catch (error) {
                console.error("Error fetching expert data:", error);
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
        return {
            expert: null,
            loading: false,
            notes: "",
            errorMessage: "",
        };
    },
});

const FullExpertComponent = defineComponent({
    template: "#full-expert-template",
    components: {
        SessionRequestComponent,
    },
    props: {
        expertId: {
            type: [Number, String],
            required: true,
        },
    },
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
    watch: {
        expertId() {
            this.loadExpert();
        },
    },
    computed: {
        hasContactInfo() {
            return (
                this.expert &&
                (this.expert.linkedin || this.expert.twitter || this.expert.email || this.expert.phone_number)
            );
        },
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        document.removeEventListener("click", this.handleOutsideClick);
    },
    methods: {
        async fetchExpert(expertId) {
            try {
                const response = await fetch(`/expert/get/${expertId}`);
                if (!response.ok) {
                    throw new Error("Failed to fetch expert data");
                }
                const data = await response.json();
                this.expert = data.expert;
                console.log("Expert data:", this.expert);
            } catch (error) {
                console.error("Error fetching expert data:", error);
            }
        },
        closeExpert() {
            this.$emit("close-expert");
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

            let earliestDate = new Date();
            qualifications.forEach((qual) => {
                if (qual.start_date) {
                    const startDate = new Date(qual.start_date);
                    if (!isNaN(startDate) && startDate < earliestDate) {
                        earliestDate = startDate;
                    }
                }
            });

            const now = new Date();
            const years = now.getFullYear() - earliestDate.getFullYear();
            return years > 0 ? years : "<1";
        },
        getQualificationColorClass(type) {
            const classes = {
                education: "bg-gradient-to-b from-blue-500 to-indigo-600",
                freelance: "bg-gradient-to-b from-green-500 to-teal-600",
                contract: "bg-gradient-to-b from-amber-500 to-orange-600",
                office: "bg-gradient-to-b from-indigo-500 to-purple-600",
                remote: "bg-gradient-to-b from-sky-500 to-blue-600",
                trainee: "bg-gradient-to-b from-pink-500 to-rose-600",
            };
            const normalizedType = type ? type.toLowerCase() : "";

            return classes[normalizedType] || classes["OTHER"] || "bg-gradient-to-b from-gray-500 to-slate-600";
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
        setDefaultImage(event, name) {
            event.target.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(name || "Expert")}&background=6366f1&color=fff&size=150`;
        },
    },
    data() {
        return {
            selectedTimeslot: null,
            selectedDate: null,
            showModal: false,
            isLoading: false,
            isExpanded: false,
            isSessionRequestOpened: false,
            expert: null,
        };
    },
});

const SessionInfoComponent = defineComponent({
    template: "#session-info-template",
    props: {
        session: {
            type: Object,
            required: true,
        },
    },
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
        async processAction(session, action) {
            try {
                const csrf_token = document.getElementById("csrf_token").value;

                const response = await fetch("/expert/session/action/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrf_token,
                    },
                    body: JSON.stringify({
                        session_id: session.id,
                        action: action,
                    }),
                });

                const data = await response.json();
                if (data.error) {
                    console.error("Error changing session status:", data.error);
                    return;
                }

                const actionMap = {
                    upcoming: "upcoming",
                    canceled: "canceled",
                };

                session.status = actionMap[action] || session.status;
                session.confirmRequested = false;

                this.$emit("close");

                this.$nextTick(() => {
                    this.$parent.sessions = [...this.$parent.sessions];
                });
            } catch (error) {
                console.error("Action failed:", error);
                return;
            }
        },
        formatDate(date) {
            const options = { year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" };
            return new Date(date).toLocaleString("en-US", options);
        },
        formatPrice(price) {
            return parseFloat(price).toLocaleString("en-US", {
                minimumFractionDigits: 0,
                maximumFractionDigits: 2,
            });
        },
        formatTime(timeString) {
            return new Date(`1970-01-01T${timeString}`).toLocaleTimeString("en-US", {
                hour: "2-digit",
                minute: "2-digit",
            });
        },
        closeSessionInfo() {
            this.$emit("close-session-info");
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeSessionInfo();
            }
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeSessionInfo();
            }
        },
    },
    data() {
        return {};
    },
});

const SessionComponent = defineComponent({
    template: "#session-template",
    computed: {
        filteredSessions() {
            if (!this.sessions.length) return null;
            const now = new Date();
            return this.types
                .filter((type) => this.filters[type])
                .map((type) => {
                    const sessions = this.sessions.filter((session) => {
                        return this.getSessionType(session) === type;
                    });
                    const sortedSessions = this.sortSessions(sessions);
                    return sessions.length ? { type, title: this.config[type].title, sessions: sortedSessions } : null;
                })
                .filter(Boolean);
        },
    },
    mounted() {
        this.fetchSessions();
        document.addEventListener("click", this.handleClickOutside);
    },
    beforeUnmount() {
        document.removeEventListener("click", this.handleClickOutside);
    },
    methods: {
        async fetchSessions() {
            try {
                const response = await fetch("/expert/get_sessions/");
                if (!response.ok) {
                    throw new Error("Failed to fetch sessions");
                }
                const { sessions } = await response.json();
                this.sessions = sessions.map((session) => ({
                    ...session,
                    confirmRequested: false,
                }));
                console.log("Fetched sessions:", this.sessions);
            } catch (error) {
                console.error("Error fetching sessions:", error);
                this.sessions = [];
            }
        },
        sortSessions(sessions) {
            return [...sessions].sort((a, b) => {
                const dateA = new Date(a.created_at);
                const dateB = new Date(b.created_at);
                return this.sortOrder === "newest" ? dateB - dateA : dateA - dateB;
            });
        },
        getSessionType(session) {
            if (session.status === "pending") return "pending";
            if (session.status === "upcoming") return "upcoming";
            if (session.status === "past" || session.status === "canceled") return "past";
            return null;
        },
        formatDate(dateString) {
            return new Date(dateString).toLocaleDateString("en-US", {
                weekday: "long",
                day: "numeric",
                month: "long",
                year: "numeric",
            });
        },
        formatTime(dateString) {
            return new Date(dateString).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
        },
        toggleSortOrder() {
            this.sortOrder = this.sortOrder === "newest" ? "oldest" : "newest";
        },
        handleClickOutside(event) {
            const dropdown = this.$refs.dropdownContainer;
            if (dropdown && !dropdown.contains(event.target)) {
                this.dropdownOpened = false;
            }
        },
    },
    data() {
        return {
            sessions: [],
            filters: { pending: true, upcoming: true, past: true },
            types: ["pending", "upcoming", "past"],
            config: {
                pending: {
                    title: "Awaiting Approval",
                    defaultText: "Approve",
                    confirmText: "Sure?",
                    baseColor: "#3b82f6",
                    confirmColor: "#22c55e",
                    nextStatus: "upcoming",
                },
                upcoming: {
                    title: "Upcoming Sessions",
                    defaultText: "Cancel",
                    confirmText: "Sure?",
                    baseColor: "#22c55e",
                    confirmColor: "#ef4444",
                    nextStatus: "past",
                },
                past: {
                    title: "Past Sessions",
                    defaultText: "Delete",
                    confirmText: "Sure?",
                    baseColor: "#ef4444",
                    confirmColor: "#b91c1c",
                    nextStatus: null,
                },
            },
            sortOrder: "newest",
            dropdownOpened: false,
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
        SessionComponent,
        SessionInfoComponent,
    },
    watch: {
        asideMinified(value) {
            localStorage.setItem("asideMinified", value);
        },
    },
    mounted() {
        document.addEventListener("click", this.handleClickOutside);
        this.asideMinified = localStorage.getItem("asideMinified") == "true";
        if (window.location.pathname.includes("/expert/list")) {
            this.loadQualificationTypes();
            this.loadExperts(1);
        }
        const expertIdElement = document.getElementById("expert-id");
        if (expertIdElement && expertIdElement.value) {
            this.expertId = expertIdElement.value;
            this.fetchExpertQualifications();
        }
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
        async loadQualificationTypes() {
            try {
                const response = await fetch("/expert/api/qualification-types");
                if (!response.ok) {
                    throw new Error("Не удалось загрузить типы квалификаций");
                }

                const data = await response.json();
                this.qualificationTypes = data.qualification_types;
            } catch (error) {
                console.error("Ошибка при загрузке типов квалификаций:", error);

                this.qualificationTypes = [
                    { value: "EDUCATION", name: "Education" },
                    { value: "FREELANCE", name: "Freelance" },
                    { value: "CONTRACT", name: "Contract" },
                    { value: "OFFICE", name: "Office" },
                    { value: "REMOTE", name: "Remote" },
                    { value: "TRAINEE", name: "Trainee" },
                ];
            }
        },
        async loadExperts(page) {
            this.loading = true;

            try {
                const queryParams = new URLSearchParams({
                    page: page,
                    per_page: this.pagination.per_page || 9,
                    expertise: this.filters.expertise === "All" ? "All" : this.filters.expertise,
                    region: this.filters.region,
                    search: this.filters.search,
                });

                const response = await fetch(`/expert/api/experts?${queryParams}`);
                if (!response.ok) {
                    throw new Error("Failed to fetch experts");
                }

                const data = await response.json();
                this.experts = data.experts;
                this.pagination = data.pagination;

                if (window.location.pathname.includes("/expert/list")) {
                    window.history.replaceState(null, "", `/expert/list?${queryParams.toString()}`);
                }
            } catch (error) {
                console.error("Error loading experts:", error);
            } finally {
                this.loading = false;
            }
        },
        async submitExpertData() {
            const csrfToken = document.getElementById("csrf_token")?.value;
            const pictureInput = document.getElementById("picture");
            const picture = pictureInput?.files[0] || null;
            const first_name = document.getElementById("first_name")?.value || "";
            const last_name = document.getElementById("last_name")?.value || "";
            const firm_name = document.getElementById("firm_name")?.value || "";
            const position = document.getElementById("position")?.value || "";
            const location = document.getElementById("location")?.value || "";
            const bio = document.getElementById("bio")?.value || "";
            const price = document.getElementById("price")?.value || "";
            const description = document.getElementById("description")?.value || "";
            const linkedin = document.getElementById("linkedin")?.value || "";
            const twitter = document.getElementById("twitter")?.value || "";
            const email = document.getElementById("email")?.value || "";
            const phone_number = document.getElementById("phone_number")?.value || "";
            const user_email = document.getElementById("searchInput")?.value || "";

            const formData = new FormData();

            formData.append("csrf_token", csrfToken);
            formData.append("first_name", first_name);
            formData.append("last_name", last_name);
            formData.append("firm_name", firm_name);
            formData.append("position", position);
            formData.append("location", location);
            formData.append("bio", bio);
            formData.append("price", price);
            formData.append("description", description);
            formData.append("linkedin", linkedin);
            formData.append("twitter", twitter);
            formData.append("email", email);
            formData.append("phone_number", phone_number);
            formData.append("user_email", user_email);
            if (picture) {
                formData.append("picture", picture);
            }

            formData.append("qualifications", JSON.stringify(this.validateQualifications()));
            formData.append("deleted_qualifications", JSON.stringify(this.deletedQualifications));

            try {
                const response = await fetch(`/expert/update/${this.expertId}`, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": csrfToken,
                    },
                    body: formData,
                });

                if (response.redirected) {
                    window.location.href = response.url;
                }
            } catch (error) {
                console.error("Error:", error);
            }
        },
        async fetchExpertQualifications() {
            try {
                const response = await fetch(`/expert/qualifications/${this.expertId}`);
                if (!response.ok) throw new Error("Failed to fetch qualifications");
                const data = await response.json();
                this.qualifications = data.map((q) => ({
                    ...q,
                    start_date: q.start_date ? q.start_date.split("T")[0] : "",
                    end_date: q.end_date ? q.end_date.split("T")[0] : "",
                }));
            } catch (error) {
                console.error("Error fetching qualifications:", error);
            }
        },
        addQualification() {
            if (this.qualifications.length >= 8) return;
            this.qualifications.push({
                type: this.qualificationTypes[0],
                title: "",
                start_date: null,
                end_date: null,
                company_description: "",
                company_name: "",
                company_url: "",
            });
        },
        removeQualification(index, q_id) {
            this.deletedQualifications.push(q_id);
            this.qualifications.splice(index, 1);
        },
        validateQualifications() {
            const valid = [];
            this.qualifications.forEach((q) => {
                if (!q.type || !q.title || !q.company_name) {
                    console.log("Missing required fields in qualification", q);
                    return;
                }
                if (q.start_date && q.end_date && q.end_date < q.start_date) {
                    console.log("End date is before start date");
                    return;
                }
                valid.push(q);
            });
            return valid;
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
        openSessionInfo(session) {
            this.isSessionInfoOpened = true;
            this.selectedSession = session;
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
            isSessionInfoOpened: false,
            selectedSession: null,
            expertId: null,
            qualificationTypes: [],
            qualifications: [],
            deletedQualifications: [],
        };
    },
}).mount("#app");
