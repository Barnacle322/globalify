    createApp({
        components: {
            AsideComponent,
            AsideMobileComponent,
            NavbarComponent,
            // AnalysisResultComponent,
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
            handleFileUpload(event) {
                this.file = event.target.files[0];
                this.filename = this.file ? this.file.name : null;
                console.log("File:", this.file);

                this.showResults = false;
                this.deck = null;
                this.scores = null;
            },
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

                    // window.location.href = data.redirect_url;
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
                    this.deck = data.deck;
                    this.scores = data.scores;
                    this.showResults = true;
                } catch (error) {
                    console.error("Error fetching deck data:", error);
                    this.uploadStatus = error.message;
                }
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
            };
        },
    }).mount("#app");
