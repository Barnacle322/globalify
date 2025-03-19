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
        if (deckId) {
            this.fetchDeck(deckId);
        } else {
            console.log("No Deck ID found in URL");
        }
    },
    methods: {
        async loadPageContent(url) {
            try {
                console.log("Fetching page content from:", url);
                const response = await fetch(url);
                console.log("Page fetch status:", response.status);
                if (!response.ok) {
                    throw new Error(`Failed to fetch page content: ${response.status}`);
                }
                const html = await response.text();
                console.log("Page content loaded:", html.substring(0, 100) + "..."); // Log snippet
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
                console.log("Fetching deck data for deckId:", deckId);
                const response = await fetch(`/deck/deck_results/${deckId}`);
                console.log("Fetch response status:", response.status);
                if (!response.ok) {
                    throw new Error(`Failed to fetch deck data: ${response.status}`);
                }
                const data = await response.json();
                this.initialCard = data.deck.json_feedback[0];
            } catch (error) {
                console.error("PDF error:", error);
            }
        },
        async renderPage(pageNumber) {
            if (!this.pdfDocument || pageNumber < 1 || pageNumber > this.totalPages) return;
        },
        getDeckIdFromPath() {
            const pathSegments = window.location.pathname.split("/").filter(Boolean);
            const deckId = pathSegments[pathSegments.length - 1]; // Get the last segment
            return isNaN(deckId) ? null : deckId; // Ensure it's a valid number
        },


            try {
                const page = await this.pdfDocument.getPage(pageNumber);
                const canvas = this.$refs.pdfCanvas;
                const containerWidth = canvas.parentElement.clientWidth;

                const viewport = page.getViewport({
                    scale: containerWidth / page.getViewport({ scale: 1 }).width,
                });

                canvas.height = viewport.height;
                canvas.width = viewport.width;

                await page.render({
                    canvasContext: canvas.getContext("2d"),
                    viewport: viewport,
                }).promise;

                this.currentPage = pageNumber;
            } catch (error) {
                console.error("Render error:", error);
            }
        },
        handleFileUpload(event) {
            this.fileData = {
                file: event.target.files[0],
                filename: event.target.files[0]?.name || null,
            };
        },
        selectFeedback(feedback) {
            this.selectedFeedback = feedback;
            this.renderPage(feedback.page_number);
        },
        selectPage(page) {
            console.log("Selected Feedback:", page);
            this.selectedPage = page;
            console.log(this.selectedPage)
            this.initialCard = null
        },
        nextPage() {
            if (this.currentPage < this.totalPages) {
                this.renderPage(this.currentPage + 1);
            }
        },
        prevPage() {
            if (this.currentPage > 1) {
                this.renderPage(this.currentPage - 1);
            console.log(this.selectedPage);
            this.initialCard = null;
            this.renderPage(feedback.page_number);
        },

        async loadPdf() {
            try {
                const appElement = document.getElementById("pdf");
                const deckData = appElement.dataset.deckPdf;

                if (!deckData) {
                    this.pdfError = "PDF data not found";
                    return;
                }

                const loadingTask = pdfjsLib.getDocument({
                    data: atob(deckData),
                    enableWorker: true,
                });

                this.pdfDocument = await loadingTask.promise;
                this.totalPages = this.pdfDocument.numPages;
                await this.renderPage(1);
            } catch (error) {
                console.error("PDF load error:", error);
                this.pdfError = "Ошибка загрузки PDF";
            }
        },

        async renderPage(num) {
            if (!this.pdfDocument || num < 1 || num > this.totalPages) return;

            try {
                const page = await this.pdfDocument.getPage(num);
                const canvas = this.$refs.pdfCanvas;
                const context = canvas.getContext("2d");

                const containerWidth = canvas.parentElement.clientWidth;
                const viewport = page.getViewport({
                    scale: containerWidth / page.getViewport({ scale: 1 }).width,
                });

                canvas.height = viewport.height;
                canvas.width = viewport.width;

                await page.render({
                    canvasContext: context,
                    viewport: viewport,
                }).promise;

                this.currentPage = num;
            } catch (error) {
                console.error("Render error:", error);
                this.pdfError = "Ошибка отображения страницы";
            }
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

        updateFeedback() {
            // This updates the feedback section based on the selected deck
            this.selectedFeedback = this.selectedDeck.feedback;
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
            currentPage: 1,
            totalPages: 0,
            initialCard: null,
        };
    },
}).mount("#app");
