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
            const removedImage = this.formData.images[index];
            if (removedImage.id) {
                this.formData.deletedImageIds.push(removedImage.id);
            }
            this.formData.images.splice(index, 1);
            console.log("After removing image at index", index, "images:", this.formData.images.map(img => ({ id: img.id, preview: img.preview })));
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
                customer_testimonials_subtitle: "",
                deletedImageIds: []
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
        this.companyId = document.getElementById("company_id")?.value || null;
        this.microwebpageId = document.getElementById("microwebpage_id")?.value || null;
        this.storageKey = `microwebpage_form_${this.companyId || "new"}`;

        if (this.microwebpageId) {
            await this.loadMicroWebPageData();
        } else {
            this.loadFormData();
        }
    },
    methods: {
        async loadMicroWebPageData() {
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
                    images: data.images?.map(img => ({
                        id: img.id,
                        preview: img.picture_url
                    })) || [],
                    cloud_logos: data.cloud_logos?.map(logo => ({
                        id: logo.id,
                        preview: logo.logo_url
                    })) || [],
                    employees: data.employees?.map(emp => ({
                        id: emp.id,
                        first_name: emp.first_name,
                        last_name: emp.last_name,
                        position: emp.position,
                        picture_url: emp.picture_url || "",
                        bio: emp.bio || "",
                        pictureFile: null
                    })) || [],
                    customers: data.customers?.map(cust => ({
                        id: cust.id,
                        first_name: cust.first_name,
                        last_name: cust.last_name,
                        position: cust.position,
                        picture_url: cust.picture_url || "",
                        feedback: cust.feedback || "",
                        pictureFile: null
                    })) || [],
                    deletedImageIds: []
                };
                this.isFirstStageValid = this.validateFirstStage();
            } catch (error) {
                console.error("Error loading MicroWebPage data:", error);
            }
        },
        loadFormData() {
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
            if (!this.microwebpageId) {
                const dataToSave = { ...this.formData };
                delete dataToSave.logoFile;
                dataToSave.images = dataToSave.images.map(img => ({ id: img.id, preview: img.preview }));
                dataToSave.cloud_logos = dataToSave.cloud_logos.map(logo => ({ id: logo.id, preview: logo.preview }));
                localStorage.setItem(this.storageKey, JSON.stringify({
                    formData: dataToSave,
                    currentPage: this.currentPage
                }));
            }
        },
        clearFormData() {
            if (!this.microwebpageId) {
                localStorage.removeItem(this.storageKey);
            }
        },
        validateFirstStage() {
            return (
                this.formData.hero_title?.trim() &&
                this.formData.hero_subtitle?.trim() &&
                this.formData.images?.length > 0
            );
        },
        changePage(pageNumber) {
            const newPage = this.currentPage + pageNumber;
            if (newPage >= 1 && newPage <= 8) {
                this.enterClass = pageNumber > 0 ? "slide-fade-in-left" : "slide-fade-in-right";
                this.leaveClass = pageNumber > 0 ? "slide-fade-out-left" : "slide-fade-out-right";
                this.currentPage = newPage;
                this.saveFormData();
            }
        },
        updateFirstStageValid(isValid) {
            this.isFirstStageValid = isValid;
        },
        async submitForm() {
            try {
                const csrfToken = document.getElementById("csrf_token").value;
                const formData = new FormData();
                const endpoint = this.microwebpageId
                    ? `/microwebpage/update/${this.microwebpageId}`
                    : `/microwebpage/create/${this.companyId}`;

                console.log("Images before submission:", this.formData.images.map(img => ({ id: img.id, preview: img.preview, hasFile: !!img.file })));
                console.log("Deleted image IDs:", this.formData.deletedImageIds);

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
                            "customers",
                            "deletedImageIds"
                        ].includes(key) &&
                        this.formData[key] !== null
                    ) {
                        formData.append(key, this.formData[key]);
                    }
                });

                ["statistics", "faq", "about_statement", "values_statement", "benefit_statement"].forEach(arrayField => {
                    if (this.formData[arrayField]?.length > 0) {
                        formData.append(arrayField, JSON.stringify(this.formData[arrayField]));
                    }
                });

                if (this.formData.logoFile) {
                    formData.append("logo", this.formData.logoFile);
                }

                this.formData.images.forEach(img => {
                    if (img.id) {
                        formData.append(`images_ids[]`, img.id);
                    }
                    if (img.file) {
                        formData.append(`images[]`, img.file);
                    }
                });

                this.formData.deletedImageIds.forEach(id => {
                    formData.append(`deleted_images[]`, id);
                });

                this.formData.cloud_logos.forEach((logo, index) => {
                    if (logo.id || logo.file) {
                        if (logo.id) {
                            formData.append(`cloud_logos[${index}][id]`, logo.id);
                        }
                        if (logo.file) {
                            formData.append(`cloud_logos[]`, logo.file);
                        }
                    }
                });

                if (this.formData.employees) {
                    this.formData.employees.forEach((employee, index) => {
                        if (employee.id) {
                            formData.append(`employees[${index}][id]`, employee.id);
                        }
                        if (employee.pictureFile) {
                            formData.append(`employees[${index}][picture]`, employee.pictureFile);
                        }
                        formData.append(`employees[${index}][first_name]`, employee.first_name || "");
                        formData.append(`employees[${index}][last_name]`, employee.last_name || "");
                        formData.append(`employees[${index}][position]`, employee.position || "");
                        formData.append(`employees[${index}][bio]`, employee.bio || "");
                    });
                }

                if (this.formData.customers) {
                    this.formData.customers.forEach((customer, index) => {
                        if (customer.id) {
                            formData.append(`customers[${index}][id]`, customer.id);
                        }
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
                    this.formData.deletedImageIds = [];
                    window.location.href = result.redirect_url;
                }
            } catch (error) {
                console.error("Error submitting form:", error);
            }
        },
        resetForm() {
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
                customer_testimonials_subtitle: "",
                deletedImageIds: []
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