const DeckUploadComponent = defineComponent({
    template: "#deck-upload-template",
    emits: ["close-deck-upload"],
    methods: {
        async analyzeFile() {
            if (!this.fileData) {
                console.log("Please select a file first");
                return;
            }

            this.isAnalyzing = true; // Show analyzing state

            try {
                const formData = new FormData();
                formData.append("file", this.fileData.file);
                formData.append("audience", this.selectedAudience);
                formData.append("formality", this.selectedFormality);
                formData.append("domain", this.selectedDomain);

                const response = await fetch("/deck/analysis", {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": document.getElementById("csrf_token").value,
                    },
                    body: formData,
                });

                if (!response.ok) throw new Error("Analysis failed");

                const data = await response.json();
                if (data.redirect_url) {
                    window.location.href = data.redirect_url;
                    return;
                }
            } catch (error) {
                console.error("Error in analyzeFile:", error.message, error.stack);
            } finally {
                this.isAnalyzing = false; // Hide analyzing state
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
    data() {
        return {
            fileData: null,
            isUploading: false,
            selectedButton: null,
            isAnalyzing: false,
            selectedAudience: "settings",
            selectedFormality: "neutral",
            selectedDomain: "business",
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
            const deckId = pathSegments[pathSegments.length - 1];

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
                    feedback: "No specific feedback for this page.",
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
                    feedback: "No specific feedback for this page.",
                };
                this.scrollToThumbnail(prevPageNum);
            }
        },
        handleScroll(event) {
            event.preventDefault();
            const container = this.$refs.thumbnailContainer;
            container.scrollLeft += event.deltaY;
        },
        openModal(modalType) {
            let title = "";
            let contentElementId = "";

            if (modalType === "summary") {
                title = "Overall Summary";
                contentElementId = "modal-summary-content";
            } else if (modalType === "goals") {
                title = "Improvement Goals";
                contentElementId = "modal-goals-content";
            } else {
                console.warn("Unknown modal type:", modalType);
                return;
            }

            const contentElement = document.getElementById(contentElementId);
            if (contentElement) {
                this.modalTitle = title;
                this.modalContent = contentElement.innerHTML;
                this.activeModal = modalType;
                document.body.style.overflow = "hidden";
            } else {
                console.error(`Modal content element not found: #${contentElementId}`);
                this.modalTitle = title;
                this.modalContent = '<p class="text-red-500">Error: Content not found.</p>';
                this.activeModal = modalType;
                document.body.style.overflow = "hidden";
            }
        },
        closeModal() {
            this.activeModal = null;
            this.modalTitle = "";
            this.modalContent = "";
            document.body.style.overflow = "";
        },
        handleEscKey(event) {
            if (event.key === "Escape" && this.activeModal) {
                this.closeModal();
            }
        },
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            openAdvanced: false,
            mainSlideLoaded: false,
            allThumbnailsLoaded: false,
            fileData: null,
            deckFile: null,
            openDropdown: null,
            selectedPage: null,
            activeModal: null,
            modalTitle: "",
            modalContent: "",
            currentPage: 1,
            totalPages: 0,
            deckFeedback: [],
            deckThumbnails: [],
            isDeckUploadOpened: false,
        };
    },
}).mount("#app");
