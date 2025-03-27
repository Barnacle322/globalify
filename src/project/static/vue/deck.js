const DeckUploadComponent = defineComponent({
    template: "#deck-upload-template",
    emits: ['close-deck-upload'],
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
        closeDeckUpload(){
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
            selectedAudience: null,
            selectedFormality: null,
            selectedDomain: null,
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
            await this.fetchDeck();
            this.initializePDFViewer();
        }
    },

    methods: {
        async fetchDeck() {
            const pathSegments = window.location.pathname.split("/").filter(Boolean);
            const deckId = pathSegments[pathSegments.length - 1];

            try {
                const response = await fetch(`/deck/file/${deckId}`);
                if (!response.ok) {
                    throw new Error("Failed to fetch deck data");
                }
                const data = await response.json();
                this.deck = data.deck;
            } catch (error) {
                console.error("Error fetching deck data:", error.message, error.stack);
            }
        },
        async initializePDFViewer() {
            if (!this.deck) console.error("PDF not found");
            try {
                pdfjsLib.GlobalWorkerOptions.workerSrc = PDF_WORKER_URL;

                this.pdfDocument = await pdfjsLib.getDocument({
                    data: atob(this.deck),
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

                const containerWidth = container.clientWidth;
                const defaultViewport = page.getViewport({ scale: 1 });
                const aspectRatio = defaultViewport.height / defaultViewport.width;

                const scale = containerWidth / defaultViewport.width;
                const viewport = page.getViewport({ scale });

                canvas.width = containerWidth;
                canvas.height = containerWidth * aspectRatio;

                await page.render({
                    canvasContext: canvas.getContext("2d"),
                    viewport: viewport,
                }).promise;

                this.currentPage = pageNumber;
            } catch (error) {
                console.error("Render error:", error);
            }
        },
        async generatedeckThumbnails() {
            if (!this.pdfDocument) return [];

            const thumbnails = [];
            const totalPages = this.pdfDocument.numPages;
            console.log(totalPages);
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
        fetchFeedback() {
            const feedbackElement = document.getElementById("feedback-data");
            if (feedbackElement) {
                this.deckFeedback = JSON.parse(feedbackElement.textContent);
            }
        },

        selectPage(page) {
            this.selectedPage = page;
            this.renderPage(page.page_number);
        },
        nextPage() {
            if (this.currentPage < this.totalPages) {
                const nextPageNum = this.currentPage + 1;
                this.renderPage(nextPageNum);
                const nextPageFeedback = this.findFeedbackByPageNumber(nextPageNum);
                if (nextPageFeedback) {
                    this.selectedPage = nextPageFeedback;
                }
            }
        },
        prevPage() {
            if (this.currentPage > 1) {
                const prevPageNum = this.currentPage - 1;
                this.renderPage(prevPageNum);
                const prevPageFeedback = this.findFeedbackByPageNumber(prevPageNum);
                if (prevPageFeedback) {
                    this.selectedPage = prevPageFeedback;
                }
            }
        },
        findFeedbackByPageNumber(pageNumber) {
            return this.deckFeedback.find((item) => item.page_number === pageNumber);
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
            deck: null,
            scores: null,
            selectedPage: null,
            currentPage: 1,
            totalPages: 0,
            deckFeedback: [],
            deckThumbnails: [],
            isDeckUploadOpened: false,
        };
    },
}).mount("#app");
