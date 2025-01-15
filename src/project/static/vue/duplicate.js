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
        formatValue: (() => {
            return (value, field = null) => {
                if (value === 0) return "0";
                if (value === null) return "None";

                if (typeof value === "number") {
                    if (field === "min_investment" || field === "max_investment") {
                        return new Intl.NumberFormat("en-US", {
                            style: "currency",
                            currency: "USD",
                        }).format(value);
                    }
                    return value.toString();
                }

                if (Array.isArray(value)) {
                    return value
                        .map((item) => item.replace(/(Industry|Round |[<>])/g, "").trim())
                        .filter(Boolean)
                        .join(", ");
                }

                return value;
            };
        })(),
        selectField(attr, source, value, comparisonIndex, innerIndex = null) {
            this.selectedFields[comparisonIndex] ??= {};

            if (["rounds", "industries"].includes(attr)) {
                if (!this.selectedFields[comparisonIndex][attr]) {
                    this.selectedFields[comparisonIndex][attr] = {
                        sources: [source],
                        values: [value],
                    };
                } else {
                    const currentSources = this.selectedFields[comparisonIndex][attr].sources;
                    const currentValues = this.selectedFields[comparisonIndex][attr].values;

                    if (currentSources.includes(source)) {
                        const index = currentSources.indexOf(source);
                        currentSources.splice(index, 1);
                        currentValues.splice(index, 1);

                        if (currentSources.length === 0) {
                            delete this.selectedFields[comparisonIndex][attr];
                        }
                    } else {
                        currentSources.push(source);
                        currentValues.push(value);
                    }
                }
            } else {
                const currentSelection = this.selectedFields[comparisonIndex][attr];
                if (currentSelection?.source === source) {
                    delete this.selectedFields[comparisonIndex][attr];
                    return;
                }
                this.selectedFields[comparisonIndex][attr] = { source, value, innerIndex };
            }
        },

        getButtonClass(field, source, comparisonIndex) {
            const selected = this.selectedFields[comparisonIndex]?.[field];

            if (["rounds", "industries"].includes(field)) {
                return selected?.sources?.includes(source) ? "bg-blue-500 text-white" : "bg-gray-200 hover:bg-gray-300";
            }

            if (selected?.source === source) return "bg-blue-500 text-white";

            const { investorA, investorB } = this.comparisons[comparisonIndex];
            return this.formatValue(investorA[field], field) === this.formatValue(investorB[field], field)
                ? "bg-blue-500 text-white"
                : "bg-gray-200 hover:bg-gray-300";
        },

        getSelectedValue(attr, comparisonIndex) {
            const selected = this.selectedFields[comparisonIndex]?.[attr];
            if (!selected) return "---";

            if (["rounds", "industries"].includes(attr)) {
                const uniqueValues = new Set();
                selected.values.forEach((valueArray) =>
                    (valueArray || []).forEach((value) =>
                        uniqueValues.add(value.replace(/(Industry|Round |[<>])/g, "").trim()),
                    ),
                );
                return Array.from(uniqueValues).join(", ") || "---";
            }

            if (selected.source === "none") return "---";

            const investor =
                selected.source === "A"
                    ? this.comparisons[comparisonIndex]?.investorA
                    : this.comparisons[comparisonIndex]?.investorB;

            const value = investor?.[attr];
            if (value === 0) return "0";
            if (value === null) return "---";

            return this.formatValue(value, attr);
        },

        initializeDefaultSelections(comparisonIndex) {
            const { investorA, investorB } = this.comparisons[comparisonIndex];

            for (const field in investorA) {
                if (field === "id") continue;

                const valueA = investorA[field];
                const valueB = investorB[field];

                // For arrays (rounds, industries)
                if (["rounds", "industries"].includes(field)) {
                    const formattedA = this.formatValue(valueA);
                    const formattedB = this.formatValue(valueB);
                    if (formattedA === formattedB && formattedA !== "None") {
                        this.selectField(field, "A", valueA, comparisonIndex);
                    }
                    continue;
                }

                // If both values are the same
                if (valueA === valueB || (valueA === 0 && valueB === 0)) {
                    this.selectField(field, "A", valueA, comparisonIndex);
                }
                // If one value is not null, but the other is null
                else if ((valueA !== null && valueB === null) || (valueA === 0 && valueB === null)) {
                    this.selectField(field, "A", valueA, comparisonIndex);
                } else if ((valueA === null && valueB !== null) || (valueA === null && valueB === 0)) {
                    this.selectField(field, "B", valueB, comparisonIndex);
                }
            }
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
            const mergedData = {
                investorAID: this.comparisons[comparisonIndex].investorA.id,
                updatedInvestor: this.selectedFields[comparisonIndex],
            };
            console.log(mergedData);
            const investorData = {
                ID: investorAID,
                first_name: mergedData.updatedInvestor.first_name.value,
                last_name: mergedData.updatedInvestor.last_name.value,
                slug: mergedData.updatedInvestor.slug.value || null,
                firm_name: mergedData.updatedInvestor.firm_name.value || null,
                position: mergedData.updatedInvestor.position.value || null,
                about: mergedData.updatedInvestor.about.value || null,
                website: mergedData.updatedInvestor.website.value || null,
                linkedin: mergedData.updatedInvestor.linkedin.value || null,
                twitter: mergedData.updatedInvestor.twitter.value || null,
                email: mergedData.updatedInvestor.email.value || null,
                phone_number: mergedData.updatedInvestor.phone_number.value || null,
                location: mergedData.updatedInvestor.location.value || null,
                n_investments: mergedData.updatedInvestor.n_investments.value || 0,
                n_exits: mergedData.updatedInvestor.n_exits.value || 0,
                min_investment: mergedData.updatedInvestor.min_investment.value || 0,
                max_investment: mergedData.updatedInvestor.max_investment.value || 0,

                rounds: await this.getEntityIds(mergedData.updatedInvestor.rounds.values[0], "rounds"),
                industries: await this.getEntityIds(mergedData.updatedInvestor.industries.values[0], "industries"),
            };

            // try {
            //     const response = await fetch("/admin/investors/update", {
            //         method: "POST",
            //         headers: {
            //             "Content-Type": "application/json",
            //         },
            //         body: JSON.stringify(mergedData),
            //     });

            //     if (response.ok) {
            //         this.comparisons.splice(comparisonIndex, 1);
            //         delete this.selectedFields[comparisonIndex];
            //     } else {
            //         console.error("Merge failed");
            //     }
            // } catch (error) {
            //     console.error("Error during merge:", error);
            // }
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
