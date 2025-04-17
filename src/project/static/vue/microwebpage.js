const MainComponent = defineComponent({
    template: "#main-component-template",
    delimiters: ["[[", "]]"],
    props: {
        formData: Object,
        isFirstStageValid: Boolean
    },
    data() {
        return {
            errors: {
                logo_url: "",
                hero_title: "",
                hero_subtitle: "",
                images: ""
            }
        };
    },
    methods: {
        validateFields() {
            let isValid = true;
            this.errors = {
                logo_url: "",
                hero_title: "",
                hero_subtitle: "",
                images: ""
            };

            if (!this.formData.hero_title?.trim()) {
                this.errors.hero_title = "Hero title is required";
                isValid = false;
            }

            if (!this.formData.hero_subtitle?.trim()) {
                this.errors.hero_subtitle = "Hero subtitle is required";
                isValid = false;
            }

            if (this.formData.images.length === 0) {
                this.errors.images = "At least one company photo is required";
                isValid = false;
            }

            this.$emit("first-stage-valid", isValid);
            return isValid;
        },
        nextPage() {
            if (this.validateFields()) {
                this.$emit("change-page", 1);
            }
        },
        goBack() {
            window.history.back();
        },
        handleLogoUpload(event) {
            const file = event.target.files[0];
            if (!file) return;

            if (!file.type.match("image/png")) {
                this.errors.logo_url = "Please upload a PNG image file";
                event.target.value = "";
                return;
            }

            this.errors.logo_url = "";
            this.formData.logoFile = file;
            const reader = new FileReader();
            reader.onload = (e) => {
                this.formData.logoPreview = e.target.result;
            };
            reader.readAsDataURL(file);
        },
        handleImageUpload(event) {
            const files = event.target.files;
            if (!files.length) return;

            for (let file of files) {
                if (!file.type.match("image.*")) {
                    this.errors.images = "Please upload valid image files";
                    continue;
                }

                const reader = new FileReader();
                reader.onload = (e) => {
                    this.formData.images.push({
                        file: file,
                        preview: e.target.result
                    });
                    this.errors.images = "";
                };
                reader.readAsDataURL(file);
            }

            event.target.value = "";
        },
        removeImage(index) {
            this.formData.images.splice(index, 1);
            if (this.formData.images.length === 0) {
                this.errors.images = "At least one company photo is required";
            }
        },
        addBenefitStatement() {
            if (!this.formData.benefit_statement) {
                this.formData.benefit_statement = [];
            }
            this.formData.benefit_statement.push({ title: "", description: "" });
        },
        removeBenefitStatement(index) {
            this.formData.benefit_statement.splice(index, 1);
        }
    },
    watch: {
        "formData.hero_title"(newVal) {
            if (newVal?.trim()) {
                this.errors.hero_title = "";
            }
        },
        "formData.hero_subtitle"(newVal) {
            if (newVal?.trim()) {
                this.errors.hero_subtitle = "";
            }
        },
        "formData.images": {
            handler(newVal) {
                if (newVal.length > 0) {
                    this.errors.images = "";
                }
            },
            deep: true
        }
    }
});

const LogoCloudComponent = defineComponent({
    template: "#logo-cloud-component-template",
    delimiters: ["[[", "]]"],
    props: {
        formData: Object
    },
    methods: {
        previousPage() {
            this.$emit("change-page", -1);
        },
        nextPage() {
            this.$emit("change-page", 1);
        },
        handleCloudLogosUpload(event) {
            const files = event.target.files;
            if (!files.length) return;

            for (let file of files) {
                if (!file.type.match("image/png")) continue;

                const reader = new FileReader();
                reader.onload = (e) => {
                    this.formData.cloud_logos.push({
                        file: file,
                        preview: e.target.result
                    });
                };
                reader.readAsDataURL(file);
            }

            event.target.value = "";
        },
        removeCloudLogo(index) {
            this.formData.cloud_logos.splice(index, 1);
        }
    }
});

const StatisticsComponent = defineComponent({
    template: "#statistics-component-template",
    delimiters: ["[[", "]]"],
    props: {
        formData: Object
    },
    methods: {
        previousPage() {
            this.$emit("change-page", -1);
        },
        nextPage() {
            this.$emit("change-page", 1);
        },
        addStatistic() {
            if (!this.formData.statistics) {
                this.formData.statistics = [];
            }
            this.formData.statistics.push({ key: "", value: "" });
        },
        removeStatistic(index) {
            this.formData.statistics.splice(index, 1);
        }
    }
});

const MissionComponent = defineComponent({
    template: "#mission-component-template",
    delimiters: ["[[", "]]"],
    props: {
        formData: Object
    },
    methods: {
        previousPage() {
            this.$emit("change-page", -1);
        },
        nextPage() {
            this.$emit("change-page", 1);
        }
    }
});

const FaqComponent = defineComponent({
    template: "#faq-component-template",
    delimiters: ["[[", "]]"],
    props: {
        formData: Object
    },
    methods: {
        previousPage() {
            this.$emit("change-page", -1);
        },
        nextPage() {
            this.$emit("change-page", 1);
        },
        addFaqItem() {
            if (!this.formData.faq) {
                this.formData.faq = [];
            }
            this.formData.faq.push({ question: "", answer: "" });
        },
        removeFaqItem(index) {
            this.formData.faq.splice(index, 1);
        }
    }
});

const AboutComponent = defineComponent({
    template: "#about-component-template",
    delimiters: ["[[", "]]"],
    props: {
        formData: Object
    },
    methods: {
        previousPage() {
            this.$emit("change-page", -1);
        },
        nextPage() {
            this.$emit("change-page", 1);
        },
        addAboutStatement() {
            if (!this.formData.about_statement) {
                this.formData.about_statement = [];
            }
            this.formData.about_statement.push({ title: "", description: "" });
        },
        removeAboutStatement(index) {
            this.formData.about_statement.splice(index, 1);
        },
        addValuesStatement() {
            if (!this.formData.values_statement) {
                this.formData.values_statement = [];
            }
            this.formData.values_statement.push({ title: "", description: "" });
        },
        removeValuesStatement(index) {
            this.formData.values_statement.splice(index, 1);
        }
    },
    mounted() {
        if (!this.formData.about_statement) {
            this.formData.about_statement = [];
        }
        if (!this.formData.values_statement) {
            this.formData.values_statement = [];
        }
    }
});

const AddEmployeeComponent = defineComponent({
    template: "#add-employee-template",
    delimiters: ["[[", "]]"],
    props: {
        formData: Object
    },
    data() {
        return {
            errors: {
                first_name: "",
                last_name: "",
                position: "",
                picture_url: "",
                bio: ""
            }
        };
    },
    methods: {
        previousPage() {
            this.$emit("change-page", -1);
        },
        nextPage() {
            if (this.validateFields()) {
                this.$emit("change-page", 1);
            }
        },
        validateFields() {
            let isValid = true;
            this.errors = {
                first_name: "",
                last_name: "",
                position: "",
                picture_url: "",
                bio: ""
            };

            if (!this.formData.employees) {
                this.formData.employees = [];
            }

            this.formData.employees.forEach(employee => {
                if (!employee.first_name?.trim()) {
                    this.errors.first_name = "First name is required";
                    isValid = false;
                }
                if (!employee.last_name?.trim()) {
                    this.errors.last_name = "Last name is required";
                    isValid = false;
                }
                if (!employee.position?.trim()) {
                    this.errors.position = "Position is required";
                    isValid = false;
                }
            });

            return isValid;
        },
        addEmployee() {
            if (!this.formData.employees) {
                this.formData.employees = [];
            }
            this.formData.employees.push({
                first_name: "",
                last_name: "",
                position: "",
                picture_url: "",
                bio: "",
                pictureFile: null
            });
        },
        removeEmployee(index) {
            this.formData.employees.splice(index, 1);
        },
        handleEmployeePhotoUpload(event, index) {
            const file = event.target.files[0];
            if (!file) return;

            if (!file.type.match("image.*")) {
                this.errors.picture_url = "Please upload a valid image file";
                event.target.value = "";
                return;
            }

            this.errors.picture_url = "";
            this.formData.employees[index].pictureFile = file;
            const reader = new FileReader();
            reader.onload = (e) => {
                this.formData.employees[index].picture_url = e.target.result;
            };
            reader.readAsDataURL(file);
        }
    },
    mounted() {
        if (!this.formData.employees) {
            this.formData.employees = [];
        }
    }
});

const AddCustomerFeedbackComponent = defineComponent({
    template: "#add-customer-feedback-template",
    delimiters: ["[[", "]]"],
    props: {
        formData: Object
    },
    data() {
        return {
            errors: {
                first_name: "",
                last_name: "",
                position: "",
                picture_url: "",
                feedback: "",
                customer_testimonials_title: "",
                customer_testimonials_subtitle: ""
            }
        };
    },
    methods: {
        previousPage() {
            this.$emit("change-page", -1);
        },
        submit() {
            if (this.validateFields()) {
                this.$emit("submit-form");
            }
        },
        validateFields() {
            let isValid = true;
            this.errors = {
                first_name: "",
                last_name: "",
                position: "",
                picture_url: "",
                feedback: "",
                customer_testimonials_title: "",
                customer_testimonials_subtitle: ""
            };

            if (!this.formData.customer_testimonials_title?.trim()) {
                this.errors.customer_testimonials_title = "Testimonials section title is required";
                isValid = false;
            }

            if (!this.formData.customer_testimonials_subtitle?.trim()) {
                this.errors.customer_testimonials_subtitle = "Testimonials section subtitle is required";
                isValid = false;
            }

            if (!this.formData.customers) {
                this.formData.customers = [];
            }

            this.formData.customers.forEach(customer => {
                if (!customer.first_name?.trim()) {
                    this.errors.first_name = "First name is required";
                    isValid = false;
                }
                if (!customer.last_name?.trim()) {
                    this.errors.last_name = "Last name is required";
                    isValid = false;
                }
                if (!customer.feedback?.trim()) {
                    this.errors.feedback = "Feedback is required";
                    isValid = false;
                }
            });

            return isValid;
        },
        addCustomer() {
            if (!this.formData.customers) {
                this.formData.customers = [];
            }
            this.formData.customers.push({
                first_name: "",
                last_name: "",
                position: "",
                picture_url: "",
                feedback: "",
                pictureFile: null
            });
        },
        removeCustomer(index) {
            this.formData.customers.splice(index, 1);
        },
        handleCustomerPhotoUpload(event, index) {
            const file = event.target.files[0];
            if (!file) return;

            if (!file.type.match("image.*")) {
                this.errors.picture_url = "Please upload a valid image file";
                event.target.value = "";
                return;
            }

            this.errors.picture_url = "";
            this.formData.customers[index].pictureFile = file;
            const reader = new FileReader();
            reader.onload = (e) => {
                this.formData.customers[index].picture_url = e.target.result;
            };
            reader.readAsDataURL(file);
        }
    },
    watch: {
        "formData.customer_testimonials_title"(newVal) {
            if (newVal?.trim()) {
                this.errors.customer_testimonials_title = "";
            }
        },
        "formData.customer_testimonials_subtitle"(newVal) {
            if (newVal?.trim()) {
                this.errors.customer_testimonials_subtitle = "";
            }
        }
    },
    mounted() {
        if (!this.formData.customers) {
            this.formData.customers = [];
        }
    }
});

createApp({
    components: {
        MainComponent,
        LogoCloudComponent,
        StatisticsComponent,
        MissionComponent,
        FaqComponent,
        AboutComponent,
        AddEmployeeComponent,
        AddCustomerFeedbackComponent
    },
    data() {
        return {
            currentPage: 1,
            enterClass: "slide-fade-in-left",
            leaveClass: "slide-fade-out-left",
            storageKey: "microwebpage_form_data",
            isFirstStageValid: false,
            companyId: null,
            microwebpageId: null,
            formData: {
                id: null,
                company_id: null,
                logoFile: null,
                logoPreview: null,
                cloud_logos: [],
                images: [],
                hero_title: "",
                hero_subtitle: "",
                logo_cloud_title: "",
                benefit_title: "",
                benefit_subtitle: "",
                benefit_statement: [],
                stat_title: "",
                stat_subtitle: "",
                statistics: [],
                mission_title: "",
                mission_statement: "",
                leadership_title: "",
                leadership_subtitle: "",
                faq_title: "",
                faq: [],
                about_title: "",
                about_subtitle: "",
                about_statement: [],
                values_title: "",
                values_subtitle: "",
                values_statement: [],
                employees: [],
                customers: [],
                customer_testimonials_title: "",
                customer_testimonials_subtitle: ""
            }
        };
    },
    computed: {
        currentComponent() {
            const components = [
                MainComponent,
                LogoCloudComponent,
                StatisticsComponent,
                MissionComponent,
                FaqComponent,
                AboutComponent,
                AddEmployeeComponent,
                AddCustomerFeedbackComponent
            ];
            return components[this.currentPage - 1];
        }
    },
    async mounted() {
        // Initialize companyId and microwebpageId from hidden inputs
        this.companyId = document.getElementById("company_id")?.value || null;
        this.microwebpageId = document.getElementById("microwebpage_id")?.value || null;
        this.storageKey = `microwebpage_form_${this.companyId || "new"}`;

        // Load data based on whether we're updating or creating
        if (this.microwebpageId) {
            await this.loadMicroWebPageData();
        } else {
            this.loadFormData();
        }
    },
    methods: {
        async loadMicroWebPageData() {
            // Load data from backend for update flow (no localStorage)
            try {
                const response = await fetch(`/microwebpage/get/data/${this.microwebpageId}`);
                if (!response.ok) {
                    throw new Error("Failed to fetch MicroWebPage data");
                }
                const data = await response.json();
                this.formData = {
                    ...this.formData,
                    ...data,
                    logoPreview: data.logo_url || null,
                    images: data.images?.map(img => ({ preview: img.picture_url })) || [],
                    cloud_logos: data.cloud_logos?.map(logo => ({ preview: logo.logo_url })) || [],
                    employees: data.employees?.map(emp => ({
                        ...emp,
                        picture_url: emp.picture_url || "",
                        pictureFile: null
                    })) || [],
                    customers: data.customers?.map(cust => ({
                        ...cust,
                        picture_url: cust.picture_url || "",
                        pictureFile: null
                    })) || []
                };
                this.isFirstStageValid = this.validateFirstStage();
            } catch (error) {
                console.error("Error loading MicroWebPage data:", error);
                alert("Failed to load MicroWebPage data. Please try again.");
            }
        },
        loadFormData() {
            // Load data from localStorage for create flow
            if (!this.microwebpageId) {
                const savedData = localStorage.getItem(this.storageKey);
                if (savedData) {
                    try {
                        const parsedData = JSON.parse(savedData);
                        this.formData = { ...this.formData, ...parsedData.formData };
                        this.currentPage = parsedData.currentPage || 1;
                    } catch (e) {
                        console.error("Failed to parse saved form data", e);
                    }
                }
            }
        },
        saveFormData() {
            // Save form data to localStorage only in create flow
            if (!this.microwebpageId) {
                const dataToSave = { ...this.formData };
                delete dataToSave.logoFile;
                dataToSave.images = dataToSave.images.map(img => ({ preview: img.preview }));
                dataToSave.cloud_logos = dataToSave.cloud_logos.map(logo => ({ preview: logo.preview }));
                localStorage.setItem(this.storageKey, JSON.stringify({
                    formData: dataToSave,
                    currentPage: this.currentPage
                }));
            }
        },
        clearFormData() {
            // Clear localStorage after successful submission (only in create flow)
            if (!this.microwebpageId) {
                localStorage.removeItem(this.storageKey);
            }
        },
        validateFirstStage() {
            // Validate first stage for navigation
            return (
                this.formData.hero_title?.trim() &&
                this.formData.hero_subtitle?.trim() &&
                this.formData.images?.length > 0
            );
        },
        changePage(pageNumber) {
            // Navigate between form steps
            const newPage = this.currentPage + pageNumber;
            if (newPage >= 1 && newPage <= 8) {
                this.enterClass = pageNumber > 0 ? "slide-fade-in-left" : "slide-fade-in-right";
                this.leaveClass = pageNumber > 0 ? "slide-fade-out-left" : "slide-fade-out-right";
                this.currentPage = newPage;
                this.saveFormData();
            }
        },
        updateFirstStageValid(isValid) {
            // Update validation status for first stage
            this.isFirstStageValid = isValid;
        },
        async submitForm() {
            // Submit form data to backend
            try {
                const csrfToken = document.getElementById("csrf_token").value;
                const formData = new FormData();
                const endpoint = this.microwebpageId
                    ? `/microwebpage/update/${this.microwebpageId}`
                    : `/microwebpage/create/${this.companyId}`;

                // Append scalar fields
                Object.keys(this.formData).forEach(key => {
                    if (
                        ![
                            "logoFile",
                            "images",
                            "cloud_logos",
                            "statistics",
                            "faq",
                            "about_statement",
                            "values_statement",
                            "benefit_statement",
                            "employees",
                            "customers"
                        ].includes(key) &&
                        this.formData[key] !== null
                    ) {
                        formData.append(key, this.formData[key]);
                    }
                });

                // Append JSON array fields
                ["statistics", "faq", "about_statement", "values_statement", "benefit_statement"].forEach(arrayField => {
                    if (this.formData[arrayField]?.length > 0) {
                        formData.append(arrayField, JSON.stringify(this.formData[arrayField]));
                    }
                });

                // Append logo file
                if (this.formData.logoFile) {
                    formData.append("logo", this.formData.logoFile);
                }

                // Append images
                this.formData.images.forEach((img, index) => {
                    if (img.file) {
                        formData.append("images[]", img.file);
                    }
                });

                // Append cloud logos
                this.formData.cloud_logos.forEach((logo, index) => {
                    if (logo.file) {
                        formData.append("cloud_logos[]", logo.file);
                    }
                });

                // Append employees
                if (this.formData.employees) {
                    this.formData.employees.forEach((employee, index) => {
                        if (employee.pictureFile) {
                            formData.append(`employees[${index}][picture]`, employee.pictureFile);
                        }
                        formData.append(`employees[${index}][first_name]`, employee.first_name || "");
                        formData.append(`employees[${index}][last_name]`, employee.last_name || "");
                        formData.append(`employees[${index}][position]`, employee.position || "");
                        formData.append(`employees[${index}][bio]`, employee.bio || "");
                    });
                }

                // Append customers
                if (this.formData.customers) {
                    this.formData.customers.forEach((customer, index) => {
                        if (customer.pictureFile) {
                            formData.append(`customers[${index}][picture]`, customer.pictureFile);
                        }
                        formData.append(`customers[${index}][first_name]`, customer.first_name || "");
                        formData.append(`customers[${index}][last_name]`, customer.last_name || "");
                        formData.append(`customers[${index}][position]`, customer.position || "");
                        formData.append(`customers[${index}][feedback]`, customer.feedback || "");
                    });
                }

                const response = await fetch(endpoint, {
                    method: "POST",
                    headers: {
                        "X-CSRF-Token": csrfToken
                    },
                    body: formData
                });

                if (!response.ok) {
                    throw new Error("Submission failed");
                }

                const result = await response.json();
                if (result.redirect_url) {
                    this.clearFormData();
                    window.location.href = result.redirect_url;
                }
            } catch (error) {
                console.error("Error submitting form:", error);
                alert("An error occurred while submitting the form. Please try again.");
            }
        },
        resetForm() {
            // Reset form to initial state
            this.formData = {
                id: null,
                company_id: null,
                logoFile: null,
                logoPreview: null,
                cloud_logos: [],
                images: [],
                hero_title: "",
                hero_subtitle: "",
                logo_cloud_title: "",
                benefit_title: "",
                benefit_subtitle: "",
                benefit_statement: [],
                stat_title: "",
                stat_subtitle: "",
                statistics: [],
                mission_title: "",
                mission_statement: "",
                leadership_title: "",
                leadership_subtitle: "",
                faq_title: "",
                faq: [],
                about_title: "",
                about_subtitle: "",
                about_statement: [],
                values_title: "",
                values_subtitle: "",
                values_statement: [],
                employees: [],
                customers: [],
                customer_testimonials_title: "",
                customer_testimonials_subtitle: ""
            };
            this.currentPage = 1;
            this.clearFormData();
        }
    },
    watch: {
        formData: {
            handler() {
                this.saveFormData();
            },
            deep: true
        }
    }
}).mount("#app");