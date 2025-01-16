createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
    },
    async beforeMount() {
        await this.fetchDuplicate();
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

        initializeDefaultSelections(comparisonIndex) {
            const { investorA, investorB } = this.comparisons[comparisonIndex];

            Object.entries(investorA).forEach(([field, valueA]) => {
                if (field === "id") return;

                const valueB = investorB[field];
                const isArrayField = ["rounds", "industries"].includes(field);

                if (isArrayField) {
                    const formattedA = this.formatValue(valueA);
                    const formattedB = this.formatValue(valueB);
                    if (formattedA === formattedB && formattedA !== "None") {
                        this.selectField(field, "A", valueA, comparisonIndex);
                    }
                    return;
                }

                if (valueA === valueB || (valueA === 0 && valueB === 0)) {
                    this.selectField(field, "A", valueA, comparisonIndex);
                } else if ((valueA !== null && valueB === null) || (valueA === 0 && valueB === null)) {
                    this.selectField(field, "A", valueA, comparisonIndex);
                } else if ((valueA === null && valueB !== null) || (valueA === null && valueB === 0)) {
                    this.selectField(field, "B", valueB, comparisonIndex);
                }
            });
        },
        async fetchDuplicate() {
            try {
                const response = await fetch("/admin/investors/get/duplicates", {
                    method: "GET",
                    headers: { "Content-Type": "application/json" },
                });

                if (!response.ok) throw new Error("Failed to fetch duplicates");

                const { comparisons } = await response.json();
                this.comparisons = comparisons.map(({ investor_a, investor_b, score }) => ({
                    investorA: investor_a,
                    investorB: investor_b,
                    score,
                }));

                this.comparisons.forEach((_, index) => {
                    this.initializeDefaultSelections(index);
                });
            } catch (error) {
                console.error("Error fetching duplicates:", error);
            }
        },
        async mergeInvestors(comparisonIndex) {
            investorAID = this.comparisons[comparisonIndex].investorA.id;
            investorBID = this.comparisons[comparisonIndex].investorB.id;
            updatedInvestor = this.selectedFields[comparisonIndex];

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

            const investorData = {
                first_name: updatedInvestor.first_name?.value || null,
                last_name: updatedInvestor.last_name?.value || null,
                slug: updatedInvestor.slug?.value + "_new" || null,
                firm_name: updatedInvestor.firm_name?.value || null,
                position: updatedInvestor.position?.value || null,
                about: updatedInvestor.about?.value || null,
                website: updatedInvestor.website?.value || null,
                linkedin: updatedInvestor.linkedin?.value || null,
                twitter: updatedInvestor.twitter?.value || null,
                email: updatedInvestor.email?.value || null,
                phone_number: updatedInvestor.phone_number?.value || null,
                location: updatedInvestor.location?.value || null,
                n_investments: updatedInvestor.n_investments?.value ?? null,
                n_exits: updatedInvestor.n_exits?.value ?? null,
                is_public: updatedInvestor.is_public?.value ?? null,
                is_approved: updatedInvestor.is_approved?.value ?? null,
                min_investment: updatedInvestor.min_investment?.value ?? null,
                max_investment: updatedInvestor.max_investment?.value ?? null,

                rounds: getUniqueIds(updatedInvestor.rounds?.values),
                industries: getUniqueIds(updatedInvestor.industries?.values),
            };
            console.log(investorData);
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch("/admin/investors/create", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },

                    body: JSON.stringify(investorData),
                });
                if (response.redirected) {
                    window.location.href = response.url;
                }
            } catch (error) {
                console.error("Error during merge:", error);
            }
        },
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            comparisons: [],
            selectedFields: {},
        };
    },
}).mount("#app");
