createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
    },
    delimiters: ["[[", "]]"],
    watch: {
        asideMinified(value) {
            localStorage.setItem("asideMinified", value);
        },
    },
    mounted() {
        document.addEventListener("click", this.handleClickOutside);
        this.asideMinified = localStorage.getItem("asideMinified") == "true";
        if (document.getElementById("pdf-viewer")) {
            this.initializePDFViewer();
        }
        const deckId = this.getDeckIdFromPath();
        this.fetchDeck(deckId);
    },
    methods: {
        async loadPageContent(url) {
            try {
                // console.log("Fetching page content from:", url);
                const response = await fetch(url);
                // console.log("Page fetch status:", response.status);
                if (!response.ok) {
                    throw new Error(`Failed to fetch page content: ${response.status}`);
                }
                const html = await response.text();
                // console.log("Page content loaded:", html.substring(0, 100) + "..."); // Log snippet
                this.currentPage = html; // Inject HTML into the DOM
                // Update browser URL without reloading
                window.history.pushState({ deckId: this.getDeckIdFromUrl(url) }, "", url);
            } catch (error) {
                console.error("Error loading page content:", error.message, error.stack);
            }
        },
        async analyzeFile() {
            if (!this.fileData) {
                console.log("Please select a file first");
                return;
            }

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

                if (!response.ok) {
                    throw new Error("Analysis failed");
                }

                const data = await response.json();
                console.log("Analysis result:", data);

                if (data.redirect_url) {
                    console.log("Redirect URL detected:", data.redirect_url);
                    // Directly redirect to the new URL
                    window.location.href = data.redirect_url;
                    return;
                }
            } catch (error) {
                console.error("Error in analyzeFile:", error.message, error.stack);
            }
        },
        async initializePDFViewer() {
            try {
                const pdfContainer = document.getElementById("pdf-viewer");
                const pdfData = pdfContainer?.dataset.deckPdf;

                if (!pdfData) console.error("PDF not found");
                pdfjsLib.GlobalWorkerOptions.workerSrc =
                    "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/5.0.375/pdf.worker.min.mjs";

                this.pdfDocument = await pdfjsLib.getDocument({
                    data: atob(pdfData),
                    enableWorker: true,
                }).promise;

                this.totalPages = this.pdfDocument.numPages;
                await this.renderPage(1);
            } catch (error) {
                console.error("PDF error:", error);
            }
        },
        async renderPage(pageNumber) {
            if (!this.pdfDocument || pageNumber < 1 || pageNumber > this.totalPages) return;

            try {
                const page = await this.pdfDocument.getPage(pageNumber);
                const canvas = this.$refs.pdfCanvas;
                const container = canvas.parentElement; // #pdf-viewer div

                // Get container dimensions
                const containerWidth = container.clientWidth;
                const containerHeight = container.clientHeight;

                // Initial viewport at scale 1
                const defaultViewport = page.getViewport({ scale: 1 });
                const pdfWidth = defaultViewport.width;

                // Scale based on width
                let scale = containerWidth / pdfWidth;
                let viewport = page.getViewport({ scale });

                // Adjust scale if height exceeds container
                if (viewport.height > containerHeight) {
                    scale = containerHeight / defaultViewport.height;
                    viewport = page.getViewport({ scale });
                }

                // Set canvas dimensions
                canvas.width = viewport.width;
                canvas.height = viewport.height;

                // Render the page
                await page.render({
                    canvasContext: canvas.getContext("2d"),
                    viewport: viewport,
                }).promise;

                this.currentPage = pageNumber;
            } catch (error) {
                console.error("Render error:", error);
            }
        },
        async fetchDeck(deckId) {
            try {
                const response = await fetch(`/deck/deck_results/${deckId}`);
                if (!response.ok) {
                    throw new Error("Failed to fetch deck data");
                }
                const data = await response.json();
                this.initialCard = data.deck.json_feedback[0];
            } catch (error) {
                console.error("Error fetching deck data:", error.message, error.stack);
                this.uploadStatus = error.message;
            }
        },
        getDeckIdFromPath() {
            const pathSegments = window.location.pathname.split("/").filter(Boolean);
            const deckId = pathSegments[pathSegments.length - 1]; // Get the last segment
            return isNaN(deckId) ? null : deckId; // Ensure it's a valid number
        },
        handleFileUpload(event) {
            this.fileData = {
                file: event.target.files[0],
                filename: event.target.files[0]?.name || null,
            };
        },
        selectPage(page) {
            this.selectedPage = page;
            this.initialCard = null;
            this.renderPage(page.page_number)
        },
        nextPage() {
            if (this.currentPage < this.totalPages) {
                this.renderPage(this.currentPage + 1);

            }
        },
        prevPage() {
            if (this.currentPage > 1) {
                this.renderPage(this.currentPage - 1);
            }
        },
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            openAdvanced: false,
            fileData: null,
            uploadStatus: null,
            selectedFeedback: null,
            currentPage: 1,
            totalPages: 0,
            deck: null,
            deck_pdf: null,
            scores: null,
            selectedPage: null,
            uploadFileComponent: false,
            selectedFeedback: null,
            currentPage: 1,
            totalPages: 0,
            initialCard: null,
        };
    },
}).mount("#app");
