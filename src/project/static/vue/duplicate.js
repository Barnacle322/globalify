createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
    },
    mounted() {
        this.fetchDuplicates();
    },
    methods: {
        formatInvestorData(investor) {
            return {
                id: investor.id,
                first_name: investor.first_name,
                last_name: investor.last_name,
                email: investor.email,
                slug: investor.slug,
                firm_name: investor.firm_name,
                about: investor.about,
                position: investor.position,
                website: investor.website,
                linkedin: investor.linkedin,
                twitter: investor.twitter,
                phone_number: investor.phone_number,
                n_investments: investor.n_investments,
                n_exits: investor.n_exits,
                min_investment: investor.min_investment,
                max_investment: investor.max_investment,
                location: investor.location,
                is_public: investor.is_public,
                is_approved: investor.is_approved,
                rounds: investor.rounds || [],
                industries: investor.industries || [],
            };
        },
        formatValue(value, field = null) {
            if (value === 0) return "0";
            if (value === null) return "None";

            if (typeof value === "number") {
                if (["min_investment", "max_investment"].includes(field)) {
                    return new Intl.NumberFormat("en-US", {
                        style: "currency",
                        currency: "USD",
                    }).format(value);
                }
                return value.toString();
            }

            if (Array.isArray(value)) {
                return value
                    .map((item) => {
                        if (item?.name) {
                            return item.name.replace(/(Industry|Round |[<>])/g, "").trim();
                        }
                        return typeof item === "string" ? item.replace(/(Industry|Round |[<>])/g, "").trim() : "";
                    })
                    .filter(Boolean)
                    .join(", ");
            }

            return value?.name?.replace(/(Industry|Round |[<>])/g, "").trim() || value?.toString() || "None";
        },
        selectField(attr, source, value, comparisonIndex, innerIndex = null) {
            if (!this.selectedFields[comparisonIndex]) {
                this.selectedFields[comparisonIndex] = {};
            }

            const isArrayField = ["rounds", "industries"].includes(attr);
            if (isArrayField) {
                this.handleArrayFieldSelection(attr, source, value, comparisonIndex);
            } else {
                this.handleSingleFieldSelection(attr, source, value, comparisonIndex, innerIndex);
            }
        },
        handleArrayFieldSelection(attr, source, value, comparisonIndex) {
            const field = this.selectedFields[comparisonIndex][attr];
            if (!field) {
                this.selectedFields[comparisonIndex][attr] = {
                    sources: [source],
                    values: [value],
                };
                return;
            }

            const sourceIndex = field.sources.indexOf(source);
            if (sourceIndex !== -1) {
                field.sources.splice(sourceIndex, 1);
                field.values.splice(sourceIndex, 1);
                if (!field.sources.length) {
                    delete this.selectedFields[comparisonIndex][attr];
                }
            } else {
                field.sources.push(source);
                field.values.push(value);
            }
        },
        handleSingleFieldSelection(attr, source, value, comparisonIndex, innerIndex) {
            const currentSelection = this.selectedFields[comparisonIndex][attr];
            if (currentSelection?.source === source) {
                delete this.selectedFields[comparisonIndex][attr];
            } else {
                this.selectedFields[comparisonIndex][attr] = { source, value, innerIndex };
            }
        },
        getButtonClass(field, source, comparisonIndex) {
            const selected = this.selectedFields[comparisonIndex]?.[field];
            const { investorA, investorB } = this.comparisons[comparisonIndex];

            if (["rounds", "industries"].includes(field)) {
                return selected?.sources?.includes(source) ? "bg-blue-500 text-white" : "bg-gray-200 hover:bg-gray-300";
            }

            const valuesMatch = this.formatValue(investorA[field], field) === this.formatValue(investorB[field], field);

            return selected?.source === source ? "bg-blue-500 text-white" : "bg-gray-200 hover:bg-gray-300";
        },
        getSelectedValue(attr, comparisonIndex) {
            const selected = this.selectedFields[comparisonIndex]?.[attr];
            if (!selected || selected.source === "none") return "---";

            if (["rounds", "industries"].includes(attr)) {
                return this.getArrayFieldValue(selected);
            }

            const investor = this.comparisons[comparisonIndex]?.[selected.source === "A" ? "investorA" : "investorB"];
            const value = investor?.[attr];

            return value === 0 ? "0" : value === null ? "---" : this.formatValue(value, attr);
        },
        getArrayFieldValue(selected) {
            const uniqueValues = new Set();
            selected.values.forEach((valueArray) => {
                if (Array.isArray(valueArray)) {
                    valueArray.forEach((value) => {
                        const processedValue = value?.name || value;
                        if (typeof processedValue === "string") {
                            uniqueValues.add(processedValue.replace(/(Industry|Round |[<>])/g, "").trim());
                        }
                    });
                }
            });
            return Array.from(uniqueValues).join(", ") || "---";
        },

        async initializeDefaultSelections(comparisonIndex) {
            const { investorA, investorB } = this.comparisons[comparisonIndex];

            this.selectedFields[comparisonIndex] = {};

            for (const [field, valueA] of Object.entries(investorA)) {
                if (field === "id") continue;

                const valueB = investorB[field];
                const isArrayField = ["rounds", "industries"].includes(field);
                const formattedA = this.formatValue(valueA, field);
                const formattedB = this.formatValue(valueB, field);

                if (formattedA === formattedB) {
                    this.selectField(field, "A", valueA, comparisonIndex);
                } else if (formattedB === "None" && formattedA !== "None") {
                    this.selectField(field, "A", valueA, comparisonIndex);
                } else if (formattedA === "None" && formattedB !== "None") {
                    this.selectField(field, "B", valueB, comparisonIndex);
                }
            }
        },
        async fetchDuplicates() {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const url = new URL("/admin/investors/get/duplicates", window.location.origin);
                url.searchParams.append("page", this.currentPage);
                url.searchParams.append("per_page", this.perPage);

                const response = await fetch(url, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify({ selected_params: this.selectedParams }),
                });

                const data = await response.json();
                this.pagination = data.pagination;
                console.log(data);
                this.comparisons = data.comparisons.map(({ investor_a, investor_b, score }) => ({
                    investorA: investor_a,
                    investorB: investor_b,
                    score,
                }));

                this.comparisons.forEach((_, index) => {
                    this.initializeDefaultSelections(index);
                });
            } catch (error) {
                if (error instanceof SyntaxError) {
                    console.error(" Check server logs.");
                } else {
                    console.error("Error fetching duplicates:", error);
                }
            }
        },
        async mergeInvestors(comparisonIndex) {
            try {
                if (!window.confirm("Are you sure you want to merge two investors into a new one?")) {
                    return;
                }
                const csrfToken = document.getElementById("csrf_token").value;
                investorAID = this.comparisons[comparisonIndex].investorA.id;
                investorBID = this.comparisons[comparisonIndex].investorB.id;
                updatedInvestor = this.selectedFields[comparisonIndex];

                const getValue = (field, defaultValue = null) => updatedInvestor[field]?.value ?? defaultValue;
                const getUniqueIds = (valueArrays) => {
                    if (!Array.isArray(valueArrays)) return [];
                    return [
                        ...new Set(
                            valueArrays.flatMap((array) =>
                                Array.isArray(array) ? array.filter((item) => item?.id).map((item) => item.id) : [],
                            ),
                        ),
                    ];
                };

                const mergedInvestorData = {
                    first_name: getValue("first_name"),
                    last_name: getValue("last_name"),
                    slug: getValue("slug"),
                    firm_name: getValue("firm_name"),
                    position: getValue("position"),
                    about: getValue("about"),
                    website: getValue("website"),
                    linkedin: getValue("linkedin"),
                    twitter: getValue("twitter"),
                    email: getValue("email"),
                    phone_number: getValue("phone_number"),
                    location: getValue("location"),
                    n_investments: getValue("n_investments"),
                    n_exits: getValue("n_exits"),
                    is_public: getValue("is_public"),
                    is_approved: getValue("is_approved"),
                    min_investment: getValue("min_investment"),
                    max_investment: getValue("max_investment"),
                    rounds: getUniqueIds(updatedInvestor.rounds?.values),
                    industries: getUniqueIds(updatedInvestor.industries?.values),
                };

                const mergeResponse = await fetch("/admin/investors/merge", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify(mergedInvestorData),
                });

                if (!mergeResponse.ok) {
                    const errorText = await mergeResponse.text();
                    throw new Error(`Merge failed: ${mergeResponse.status} - ${errorText}`);
                }

                // If merging is ok, than delete two duplicates in parallel
                if (mergeResponse.ok) {
                    const deleteResponses = await Promise.all([
                        fetch(`/admin/investors/${investorAID}/delete`, {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                                "X-CSRFToken": csrfToken,
                            },
                        }),
                        fetch(`/admin/investors/${investorBID}/delete`, {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                                "X-CSRFToken": csrfToken,
                            },
                        }),
                    ]);
                }

                if (mergeResponse.redirected && deleteResponses.ok) {
                    window.location.href = mergeResponse.url;
                }
            } catch (error) {
                console.error("Error during merge:", error);
            }
        },
        goToPage(page) {
            if (page !== this.currentPage) {
                this.currentPage = page;
                this.fetchDuplicates();
            }
        },
        goToPrevPage() {
            if (this.pagination?.has_prev) {
                this.currentPage = this.pagination.prev;
                this.fetchDuplicates();
            }
        },
        goToNextPage() {
            if (this.pagination?.has_next) {
                this.currentPage = this.pagination.next;
                this.fetchDuplicates();
            }
        },
        goToFirstPage() {
            this.currentPage = 1;
            this.fetchDuplicates();
        },
        goToLastPage() {
            if (this.pagination) {
                this.currentPage = this.pagination.last_page;
                this.fetchDuplicates();
            }
        },
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            comparisons: [],
            selectedFields: {},
            selectedParams: ["first_name", "last_name"],
            availableParams: ["first_name", "last_name", "firm_name", "email", "twitter", "linkedin"],
            showHelp: false,
            currentPage: 1,
            perPage: 4,
            pagination: null,
        };
    },
}).mount("#app");
