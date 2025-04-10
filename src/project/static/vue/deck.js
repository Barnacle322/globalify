const DeleteFeedbackComponent = defineComponent({
    template: "#delete-feedback-template",
    props: {
        feedbackId: {
            type: Number,
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
        async deleteFeedback(feedbackId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/deck/feedback/delete/${feedbackId}`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.redirected) {
                    window.location.href = response.url;
                } else if (response.ok) {
                    this.$emit("close-deck");
                }
            } catch (error) {
                console.error("Error cancelling invitation:", error.message);
            }
        },
        closeFeedback() {
            this.$emit("close-delete-feedback");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeFeedback();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeFeedback();
            }
        },
    },
});

const DeckSummaryComponent = defineComponent({
    template: "#deck-summary-template",
    props: {
        deckId: {
            type: Number,
            required: true,
        },
    },
    emits: ["close-deck-summary"],
    async mounted() {
        await this.fetchSummary();
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
        async fetchSummary() {
            this.isLoading = true;
            try {
                const response = await fetch(`/deck/scores/${this.deckId}`, {
                    method: "GET",
                    headers: {
                        "Content-Type": "application/json",
                    },
                });
                if (!response.ok) {
                    throw new Error("Failed to fetch goals");
                }
                const data = await response.json();

                this.summaryData = data.summary;
                this.scoreItems = [
                    { key: "grammar_score", label: "Spelling & Grammar" },
                    { key: "storytelling_score", label: "Storytelling" },
                    { key: "clarity_score", label: "Clarity" },
                    { key: "design_score", label: "Design" },
                    { key: "engagement_score", label: "Engagement" },
                ];
            } catch (error) {
                console.error("Error fetching summary:", error.message);
                this.error = error.message || "Failed to load summary. Please try again later.";
            } finally {
                this.isLoading = false;
            }
        },
        closeSummary() {
            this.$emit("close-deck-summary");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeSummary();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeSummary();
            }
        },
        getScoreBgColorClass(score) {
            if (score === null || score === undefined) return "bg-gray-300";
            if (score >= 80) return "bg-sky-500";
            if (score >= 60) return "bg-green-500";
            if (score >= 40) return "bg-yellow-500";
            return "bg-orange-500";
        },
        getScoreTextColorClass(score) {
            if (score === null || score === undefined) return "text-gray-500";
            if (score >= 80) return "text-sky-600";
            if (score >= 60) return "text-green-600";
            if (score >= 40) return "text-yellow-600";
            return "text-red-600";
        },
        getScoreWidthStyle(score) {
            const width = score && score > 0 ? score : 0;
            return { width: `${Math.min(Math.max(width, 0), 100)}%` };
        },
        formatScore(score) {
            if (score === null || score === undefined) return "0.0";
            return `${score / 10}/10`;
        },
        formatOverallScore(score) {
            if (score === null || score === undefined) return "0.0";
            return typeof score === "number" ? score.toFixed(1) : "0.0";
        },
    },
    data() {
        return {
            isLoading: true,
            summaryData: null,
            scoreItems: [],
        };
    },
});

const DeckHistoryComponent = defineComponent({
    components: {
        DeleteFeedbackComponent,
    },
    template: "#deck-history-template",
    props: {
        userId: {
            type: Number,
            required: true,
        },
        deckId: {
            type: Number,
            required: true,
        },
    },
    async mounted() {
        await this.fetchHistory();
        window.addEventListener("keydown", this.handleKeyDown);
        setTimeout(() => {
            document.addEventListener("click", this.handleOutsideClick);
        }, 0);
        window.addEventListener("click", this.closeDropdown);
    },
    async created() {
        const pathSegments = window.location.pathname.split("/").filter(Boolean);

        const deckId = pathSegments[pathSegments.length - 1];
        console.log("Path segments:", deckId);
        this.selectedHistory = deckId;
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        document.removeEventListener("click", this.handleOutsideClick);
        window.removeEventListener("click", this.closeDropdown);
    },
    methods: {
        async fetchHistory() {
            try {
                const response = await fetch(`/deck/feedbacks/${this.userId}`, {
                    method: "GET",
                    headers: {
                        "Content-Type": "application/json",
                    },
                });
                if (!response.ok) {
                    throw new Error("Failed to fetch history");
                }
                const data = await response.json();
                console.log("History data:", data);
                this.histories = data.feedbacks;
            } catch (error) {
                console.error("Error fetching history:", error.message);
                this.error = "Failed to load history. Please try again later.";
            }
            this.isLoading = false;
        },
        selectHistory(feedbackId) {
            this.selectedHistory = feedbackId;
            this.closeHistory();
        },
        closeHistory() {
            this.$emit("close-deck-history");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeHistory();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeHistory();
            }
        },
        handleHistoryClick(historyItem) {
            this.$emit("history-selected", historyItem);
            this.closeHistory();
        },
        openDropdown(feedbackId) {
            this.openedDropdownFeedbackId = feedbackId;
            this.ignoreNextOutsideClick = true;
        },
        closeDropdown(event) {
            if (this.openedDropdownFeedbackId && !this.ignoreNextOutsideClick) {
                this.openedDropdownFeedbackId = null;
            }
            this.ignoreNextOutsideClick = false;
        },
    },
    data() {
        return {
            histories: [],
            selectedHistory: null,
            isLoading: true,
            error: null,
            openedDropdownFeedbackId: null,
            ignoreNextOutsideClick: false,
            isExpanded: false,
            feedbackToDelete: null,
            deleteFeedbackOpened: false,
        };
    },
});
const DeckGoalsComponent = defineComponent({
    template: "#deck-goals-template",
    props: ["deck-id", "feed-back-id"],
    async mounted() {
        await this.fetchGoals();
        window.addEventListener("keydown", this.handleKeyDown);
        setTimeout(() => {
            document.addEventListener("click", this.handleOutsideClick);
        }, 0);
        this.initialGoals = { ...this.selectedGoals };
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        document.removeEventListener("click", this.handleOutsideClick);
    },
    computed: {
        firstCategory() {
            return Object.keys(this.categoryOptions)[0];
        },
        lastCategory() {
            const categories = Object.keys(this.categoryOptions);
            return categories[categories.length - 1];
        },
        isReady() {
            return !this.isLoading && !this.error;
        },
        areGoalsDisabled() {
            return this.selectedGoals.agent !== "";
        },
        hasChanges() {
            return (
                this.selectedGoals.audience !== this.initialGoals.audience ||
                this.selectedGoals.formality !== this.initialGoals.formality ||
                this.selectedGoals.domain !== this.initialGoals.domain ||
                this.selectedGoals.agent !== this.initialGoals.agent
            );
        },
    },
    methods: {
        async reanalizeFile() {
            this.isAnalyzing = true;
            try {
                const formData = new FormData();
                formData.append("audience", this.selectedGoals.audience);
                formData.append("formality", this.selectedGoals.formality);
                formData.append("domain", this.selectedGoals.domain);
                formData.append("agent", this.selectedGoals.agent);
                formData.append("deck_id", this.deckId);

                const response = await fetch("/deck/analysis", {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": document.getElementById("csrf_token").value,
                    },
                    body: formData,
                });

                if (!response.ok) {
                    throw new Error("Failed to re-analyze file");
                }

                if (response.redirected) {
                    window.location.href = response.url;
                    return;
                }

                const data = await response.json();
                if (data.redirect_url) {
                    window.location.href = data.redirect_url;
                    return;
                }

                this.closeGoals();
            } catch (error) {
                console.error("Error in re-analyzeFile:", error.message);
            } finally {
                this.isAnalyzing = false;
            }
        },
        async fetchGoals() {
            try {
                const response = await fetch(`/deck/feedback/${this.feedBackId}/goals`, {
                    method: "GET",
                    headers: {
                        "Content-Type": "application/json",
                    },
                });
                if (!response.ok) {
                    throw new Error("Failed to fetch goals");
                }
                const data = await response.json();
                this.processGoals(data.goals);
            } catch (error) {
                console.error("Error fetching goals:", error.message);
                this.error = "Failed to load goals. Please try again later.";
            } finally {
                this.isLoading = false;
            }
        },
        processGoals(goals) {
            this.selectedGoals = {
                audience: goals?.audience || "Investors",
                formality: goals?.formality || "Neutral",
                domain: goals?.domain || "General",
                agent: goals?.agent || "",
            };
            this.initialGoals = { ...this.selectedGoals };
        },
        closeGoals() {
            this.$emit("close-deck-goals");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeGoals();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeGoals();
            }
        },
        updateGoal(category, value) {
            if (category === "agent") {
                if (this.selectedGoals.agent === value) {
                    this.selectedGoals.agent = "";
                    if (this.originalGoals) {
                        this.selectedGoals.audience = this.originalGoals.audience;
                        this.selectedGoals.formality = this.originalGoals.formality;
                        this.selectedGoals.domain = this.originalGoals.domain;
                    }
                } else {
                    if (!this.originalGoals) {
                        this.originalGoals = { ...this.selectedGoals };
                    }
                    this.selectedGoals.agent = value;
                    this.selectedGoals.audience = "";
                    this.selectedGoals.formality = "";
                    this.selectedGoals.domain = "";
                }
            } else if (!this.selectedGoals.agent) {
                this.selectedGoals[category] = value;
            }
        },
        handleAnalyze() {
            if (this.hasChanges) {
                this.reanalizeFile();
            }
        },
    },
    data() {
        return {
            isLoading: true,
            isAnalyzing: false,
            error: null,
            originalGoals: null,
            selectedGoals: {
                audience: "Customers",
                formality: "Neutral",
                domain: "General",
                agent: "",
            },
            initialGoals: {
                audience: "",
                formality: "",
                domain: "",
                agent: "",
            },
            previousGoals: null,
            categoryLabels: {
                audience: "Audience",
                formality: "Formality",
                domain: "Domain",
                agent: "Agent",
            },
            categoryOptions: {
                audience: [
                    { value: "investors", label: "Investors" },
                    { value: "customers", label: "Customers" },
                    { value: "partners", label: "Partners" },
                ],
                formality: [
                    { value: "informal", label: "Informal" },
                    { value: "neutral", label: "Neutral" },
                    { value: "formal", label: "Formal" },
                ],
                domain: [
                    { value: "academic", label: "Academic" },
                    { value: "general", label: "General" },
                    { value: "business", label: "Business" },
                ],
                agent: [
                    { value: "steve_jobs", label: "Steve Jobs" },
                    { value: "elon_musk", label: "Elon Musk" },
                    { value: "warren_buffett", label: "Warren Buffett" },
                ],
            },
            descriptions: {
                audience: {
                    investors: "Tailored for investors and financial stakeholders.",
                    customers: "Focused on customer needs and product benefits.",
                    partners: "Designed for business partners and collaborations.",
                },
                formality: {
                    informal: "Casual tone, suitable for friendly or relaxed audiences.",
                    neutral: "Balanced tone, appropriate for general communication.",
                    formal: "Professional tone, ideal for official or academic purposes.",
                },
                domain: {
                    academic: "Structured for educational or research-based content.",
                    business: "Focused on corporate or professional presentations.",
                    general: "Versatile for a wide range of topics and audiences.",
                },
                agent: {
                    steve_jobs: "Communicate with the visionary style and product focus of Steve Jobs.",
                    elon_musk: "Adopt the innovative and future-oriented perspective of Elon Musk.",
                    warren_buffett: "Write with the practical wisdom and value-based approach of Warren Buffett.",
                },
            },
        };
    },
});

const DeleteDeckComponent = defineComponent({
    template: "#delete-deck-template",
    props: {
        deckId: {
            type: Number,
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
        async deleteDeck(deckId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/deck/delete/${deckId}`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.redirected) {
                    window.location.href = response.url;
                } else if (response.ok) {
                    this.$emit("close-deck");
                }
            } catch (error) {
                console.error("Error cancelling invitation:", error.message);
            }
        },
        closeDeck() {
            this.$emit("close-delete-deck");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeDeck();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeDeck();
            }
        },
    },
});

const DeckUploadComponent = defineComponent({
    template: "#deck-upload-template",
    components: {
        DeckGoalsComponent,
    },
    data() {
        return {
            fileData: null,
            isAnalyzing: false,
            selectedGoals: null,
        };
    },
    methods: {
        handleFileUpload(event) {
            this.fileData = {
                file: event.target.files[0],
                filename: event.target.files[0]?.name || null,
            };
        },
        updateGoals(newGoals) {
            this.selectedGoals = { ...newGoals };
        },
        async analyzeFile() {
            if (!this.fileData) {
                console.log("Please select a file first");
                return;
            }

            if (!this.selectedGoals) {
                console.log("Please select goals or an agent");
                return;
            }

            this.isAnalyzing = true;

            try {
                const formData = new FormData();
                formData.append("file", this.fileData.file);

                formData.append("audience", this.selectedGoals.audience);
                formData.append("formality", this.selectedGoals.formality);
                formData.append("domain", this.selectedGoals.domain);
                formData.append("agent", this.selectedGoals.agent);

                const response = await fetch("/deck/analysis", {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": document.getElementById("csrf_token").value,
                    },
                    body: formData,
                });

                if (!response.ok) {
                    throw new Error("Failed to analyze file");
                }

                if (response.redirected) {
                    window.location.href = response.url;
                    return;
                }

                const data = await response.json();
                if (data.redirect_url) {
                    window.location.href = data.redirect_url;
                    return;
                }
            } catch (error) {
                console.error("Error in analyzeFile:", error.message, error.stack);
            } finally {
                this.isAnalyzing = false;
            }
        },
        handleFileUpload(event) {
            this.fileData = {
                file: event.target.files[0],
                filename: event.target.files[0]?.name || null,
            };
        },
        closeDeckUpload() {
            this.$emit("close-deck-upload");
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeDeckUpload();
            }
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeDeckUpload();
            }
        },
        updateDescription(type, value) {
            this[`selected${type}`] = value;
            this.activeDescriptions[type] = this.descriptions[type][value];
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
    },
    data() {
        return {
            fileData: null,
            isUploading: false,
            selectedButton: null,
            isAnalyzing: false,
            selectedGoals: {
                audience: "Customers",
                formality: "Neutral",
                domain: "General",
                agent: "",
            },
        };
    },
});

PDF_WORKER_URL = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/5.0.375/pdf.worker.min.mjs";
createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
        DeckUploadComponent,
        DeleteDeckComponent,
        DeckGoalsComponent,
        DeckHistoryComponent,
        DeckSummaryComponent,
    },
    delimiters: ["[[", "]]"],
    watch: {
        asideMinified(value) {
            localStorage.setItem("asideMinified", value);
        },
    },
    async mounted() {
        document.addEventListener("click", this.handleClickOutside);
        this.asideMinified = localStorage.getItem("asideMinified") == "true";
        if (document.getElementById("canvas")) {
            this.fetchFeedback();
            await this.fetchDeckFile();
            this.initializePDFViewer();
            window.addEventListener("keydown", this.handleEscKey);
        }
    },
    beforeUnmount() {
        document.removeEventListener("click", this.handleClickOutside);
        window.removeEventListener("keydown", this.handleEscKey);
    },
    methods: {
        async fetchDeckFile() {
            const pathSegments = window.location.pathname.split("/").filter(Boolean);
            console.log("Path segments:", pathSegments);
            const deckId = pathSegments[pathSegments.length - 3];

            try {
                const response = await fetch(`/deck/file/${deckId}`);
                if (!response.ok) {
                    throw new Error("Failed to fetch deck data");
                }
                const data = await response.json();
                this.deckFile = data.deck;
            } catch (error) {
                console.error("Error fetching deck data:", error.message, error.stack);
            }
        },
        async initializePDFViewer() {
            if (!this.deckFile) console.error("PDF not found");
            try {
                pdfjsLib.GlobalWorkerOptions.workerSrc = PDF_WORKER_URL;

                this.pdfDocument = await pdfjsLib.getDocument({
                    data: atob(this.deckFile),
                    enableWorker: true,
                }).promise;

                this.totalPages = this.pdfDocument.numPages;
                await this.renderPage(1);
                this.mainSlideLoaded = true;

                if (this.deckFeedback.length) {
                    this.selectedPage = this.deckFeedback[0];
                }

                this.deckThumbnails = await this.generatedeckThumbnails();
                console.log("Thumbnails generated:", this.deckThumbnails);
                this.allThumbnailsLoaded = true;
            } catch (error) {
                console.error("PDF initialization failed:", error);
            }
        },
        async renderPage(pageNumber) {
            if (!this.pdfDocument || pageNumber < 1 || pageNumber > this.totalPages) return;

            try {
                const page = await this.pdfDocument.getPage(pageNumber);
                const canvas = this.$refs.pdfCanvas;
                const container = canvas.parentElement;

                const maxWidth = container.clientWidth;
                const maxHeight = container.clientHeight;

                const viewport = page.getViewport({ scale: 1 });
                const scale = Math.min(maxWidth / viewport.width, maxHeight / viewport.height);

                const renderViewport = page.getViewport({ scale });

                canvas.width = renderViewport.width;
                canvas.height = renderViewport.height;

                await page.render({
                    canvasContext: canvas.getContext("2d"),
                    viewport: renderViewport,
                }).promise;

                this.currentPage = pageNumber;
                this.selectedPage = this.findFeedbackByPageNumber(pageNumber);
            } catch (error) {
                console.error("Render error:", error);
            }
        },
        async generatedeckThumbnails() {
            if (!this.pdfDocument) return [];

            const thumbnails = [];
            const totalPages = this.pdfDocument.numPages;

            for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
                try {
                    const page = await this.pdfDocument.getPage(pageNum);
                    const canvas = document.createElement("canvas");
                    const context = canvas.getContext("2d");
                    const viewport = page.getViewport({ scale: 0.2 });

                    canvas.width = viewport.width;
                    canvas.height = viewport.height;

                    await page.render({
                        canvasContext: context,
                        viewport: viewport,
                    }).promise;

                    thumbnails.push({
                        pageNumber: pageNum,
                        imageData: canvas.toDataURL("image/png"),
                    });
                } catch (error) {
                    console.error(`Error generating thumbnail for page ${pageNum}:`, error);
                }
            }

            return thumbnails;
        },
        async getLatestFeedbackId(deckId) {
            try {
                const response = await fetch(`/deck/get/latest/feedback/${deckId}`, {
                    method: "GET",
                    headers: {
                        "Content-Type": "application/json",
                    },
                });
                if (!response.ok) {
                    throw new Error("Failed to fetch feedback");
                }
                const data = await response.json();
                this.latestFeedbackId = data.feedback_id;
            } catch (error) {
                console.error("Error fetching feedback:", error.message);
                return null;
            }
        },
        async openDeckFeedbacks(deckId) {
            await this.getLatestFeedbackId(deckId);
            if (this.latestFeedbackId) {
                window.location.href = `/deck/${deckId}/feedback/${this.latestFeedbackId}`;
            } else {
                throw new Error("No feedback found for this deck.");
            }
        },
        async saveDeckName(deckId) {
            if (this.newDeckName.trim() === "") return;
            try {
                const response = await fetch(`/deck/edit/${deckId}`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": document.getElementById("csrf_token").value,
                    },
                    body: JSON.stringify({ deck_id: deckId, new_name: this.newDeckName }),
                });
                if (!response.ok) {
                    throw new Error("Edit error");
                }
                deck.name = this.newDeckName;
                this.editingDeckId = null;
            } catch (error) {
                console.error("Edit error:", error.message);
            }
        },
        scrollToThumbnail(pageNumber) {
            this.$nextTick(() => {
                const container = this.$refs.thumbnailContainer;
                if (!container) {
                    console.warn("Thumbnail container ref not found for scrolling.");
                    return;
                }
                const targetThumbnail = container.querySelector(`[data-page-number="${pageNumber}"]`);

                if (targetThumbnail) {
                    targetThumbnail.scrollIntoView({
                        behavior: "smooth",
                        block: "nearest",
                        inline: "center",
                    });
                } else {
                    console.warn(`Thumbnail element for page ${pageNumber} not found.`);
                }
            });
        },
        fetchFeedback() {
            const feedbackElement = document.getElementById("feedback-data");
            console.log("Feedback element:", feedbackElement);
            if (feedbackElement) {
                this.deckFeedback = JSON.parse(feedbackElement.textContent);
            }
        },
        findFeedbackByPageNumber(pageNumber) {
            return this.deckFeedback.find((item) => item.page_number === pageNumber);
        },
        findFeedbackByPageNumber(pageNumber) {
            return this.deckFeedback.find((item) => item.page_number === pageNumber);
        },
        selectPage(page) {
            this.selectedPage = page;
            this.renderPage(page.page_number);
            this.scrollToThumbnail(page.page_number);
        },
        nextPage() {
            if (this.currentPage < this.totalPages) {
                const nextPageNum = this.currentPage + 1;
                this.renderPage(nextPageNum);
                const nextPageFeedback = this.findFeedbackByPageNumber(nextPageNum);
                this.selectedPage = nextPageFeedback || {
                    page_number: nextPageNum,
                    feedback: "No feedback for this page.",
                    clarity: null,
                    grammar: null,
                    design: null,
                    storytelling: null,
                    engagement: null,
                };
                this.scrollToThumbnail(nextPageNum);
            }
        },
        prevPage() {
            if (this.currentPage > 1) {
                const prevPageNum = this.currentPage - 1;
                this.renderPage(prevPageNum);
                const prevPageFeedback = this.findFeedbackByPageNumber(prevPageNum);
                this.selectedPage = prevPageFeedback || {
                    page_number: prevPageNum,
                    feedback: "No feedback for this page.",
                    clarity: null,
                    grammar: null,
                    design: null,
                    storytelling: null,
                    engagement: null,
                };
                this.scrollToThumbnail(prevPageNum);
            }
        },
        getScoreBgColorClass(score) {
            if (score === null || score === undefined) return "bg-gray-300";
            if (score >= 80) return "bg-sky-500";
            if (score >= 60) return "bg-green-500";
            if (score >= 40) return "bg-yellow-500";
            return "bg-orange-500";
        },
        getScoreWidthStyle(score) {
            const width = score && score > 0 ? score : 0;
            return { width: `${Math.min(Math.max(width, 0), 100)}%` };
        },
        formatScore(score) {
            if (score === null || score === undefined) return "0.0";
            return `${score / 10}/10`;
        },
        handleScroll(event) {
            event.preventDefault();
            const container = this.$refs.thumbnailContainer;
            container.scrollLeft += event.deltaY;
        },
        handleEscKey(event) {
            if (event.key === "Escape" && this.activeModal) {
                this.closeModal();
            }
        },
        toggleDropdown(deckId) {
            this.openedDropdownDeckId = this.openedDropdownDeckId === deckId ? null : deckId;
        },
        handleClickOutside(event) {
            const dropdown = this.$refs.dropdown;
            if (dropdown && !dropdown.contains(event.target)) {
                this.openedDropdownDeckId = null;
            }
        },
        startEditing(deckId) {
            this.editingDeckId = deckId;
            this.newDeckName = deck.name || "No Name Available";
            this.openedDropdownDeckId = null;
            this.$nextTick(() => {
                this.$refs[`nameInput-${deck.id}`][0].focus();
            });
        },
        cancelEditing() {
            this.editingDeckId = null;
            this.newDeckName = "";
        },
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            openAdvanced: false,
            mainSlideLoaded: false,
            allThumbnailsLoaded: false,
            isDeckHistoryOpened: false,
            isDeckSummaryOpened: false,
            fileData: null,
            deckFile: null,
            openDropdown: null,
            selectedPage: {
                page_number: null,
                feedback: "",
                clarity: null,
                grammar: null,
                design: null,
                storytelling: null,
                engagement: null,
            },
            activeModal: null,
            modalTitle: "",
            modalContent: "",
            currentPage: 1,
            totalPages: 0,
            deckFeedback: [],
            deckThumbnails: [],
            scoreItems: [
                { key: "clarity", label: "Clarity" },
                { key: "grammar", label: "Grammar" },
                { key: "design", label: "Design" },
                { key: "storytelling", label: "Storytelling" },
                { key: "engagement", label: "Engagement" },
            ],
            isDeckGoalsOpened: false,
            isDeckUploadOpened: false,
            openedDropdownDeckId: null,
            editingDeckId: null,
            newDeckName: "",
            deckToDelete: null,
            deleteDeckOpened: false,
            selectedDeckId: null,
            latestFeedbackId: null,
        };
    },
}).mount("#app");
