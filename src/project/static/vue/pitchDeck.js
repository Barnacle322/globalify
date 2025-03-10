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
        handleFileUpload(event) {
            this.file = event.target.files[0];
            this.filename = this.file ? this.file.name : null;
            console.log("File:", this.file);
        },
        async uploadFile() {
            if (!this.file) {
                this.uploadStatus = "Loading.";
                return;
            }

            const formData = new FormData();
            formData.append("file", this.file);

            try {
                const response = await fetch("/pitchdeck/upload", {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": document.getElementById("csrf_token").value,
                    },
                    body: formData,
                });

                if (response.ok) {
                    this.uploadStatus = "Success!";
                    this.filename = null;
                    this.file = null;
                } else {
                    const data = await response.json();
                    this.uploadStatus = `Error: ${data.message || response.statusText}`;
                }
            } catch (error) {
                console.error("Error:", error);
                this.uploadStatus = error;
            }
        },
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            openAdvanced: false,

            filename: null,
            file: null,
            uploadStatus: null,
        };
    },
}).mount("#app");
