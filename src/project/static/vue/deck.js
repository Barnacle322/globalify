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
    },
    methods: {
        async analyzeFile() {
            if (!this.file) {
                this.uploadStatus = "Please select a file first";
                return;
            }
            this.uploadStatus = "Analyzing...";

            const formData = new FormData();
            formData.append("file", this.file);

            try {
                const response = await fetch("/deck/analysis", {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": document.getElementById("csrf_token").value,
                    },
                    body: formData,
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || "Analysis failed");
                }

                window.location.href = data.redirect_url;
            } catch (error) {
                console.error("Error:", error);
                this.uploadStatus = error.message;
            }
        },
        async fetchDeck(deckId) {
            try {
                const response = await fetch(`/deck_results/${deckId}`);
                if (!response.ok) {
                    throw new Error("Failed to fetch deck data");
                }
                const data = await response.json();
                console.lo(data);
                this.deck = data.deck;
                this.pdfBase64 = data.pdf_base64;
                this.scores = data.scores;
                this.showResults = true;
            } catch (error) {
                console.error("Error fetching deck data:", error);
                this.uploadStatus = error.message;
            }
        },
        handleFileUpload(event) {
            this.file = event.target.files[0];
            this.filename = this.file ? this.file.name : null;
            console.log("File:", this.file);

            this.showResults = false;
            this.deck = null;
            this.scores = null;
        },
        displayPdf() {
            if (!this.pdfBase64) return;
            pdfjsLib.GlobalWorkerOptions.workerSrc = "//mozilla.github.io/pdf.js/build/pdf.worker.mjs";
            const canvas = document.getElementById("pdf-canvas");
            const context = canvas.getContext("2d");
            console.log("///////////////");
            // Load PDF using base64
            pdfjsLib.getDocument(this.pdfBase64).promise.then((pdf) => {
                // Fetch the first page
                pdf.getPage(1).then((page) => {
                    const viewport = page.getViewport({
                        scale: 1.5,
                    }); // Adjust scale as needed
                    canvas.height = viewport.height;
                    canvas.width = viewport.width;

                    // Render the page on the canvas
                    const renderContext = {
                        canvasContext: context,
                        viewport: viewport,
                    };
                    page.render(renderContext);
                });
            });
        },
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            openAdvanced: false,
            showResults: false,
            file: null,
            filename: null,
            uploadStatus: null,
            deck: null,
            scores: null,
            pdfBase64: null,
        };
    },
}).mount("#app");
