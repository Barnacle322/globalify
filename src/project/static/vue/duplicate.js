createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
    },
    async created() {
        console.log("3///////////////");
        // this.comparisons = this.initialData.map((comparison) => ({
        //     investorA: comparison.investor_a,
        //     investorB: comparison.investor_b,
        //     score: comparison.score,
        // }));
        await this.fetchDuplicate();
        console.log(this.comparisons);
    },
    methods: {
        formatInvestorData(investor) {
            console.log("1///////////////");
            return {
                id: investor.id,
                first_name: investor.first_name,
                last_name: investor.last_name,
                email: investor.email,
                firm_name: investor.firm_name,
                rounds: investor.rounds || [],
                industries: investor.industries || [],
                position: investor.position,
                linkedin: investor.linkedin,
                twitter: investor.twitter,
                location: investor.location,
            };
        },
        isNoneValues(valueA, valueB) {
            return valueA === null && valueB === null;
        },
        formatValue(value, field) {
            if (value === null) return "None";
            if (["rounds", "industries"].includes(field)) {
                return String(value).replace(/<|>|\[|\]|Industry|Round /g, "");
            }
            return value;
        },
        selectField(field, source, value, comparisonIndex) {
            if (!this.selectedFields[comparisonIndex]) {
                this.selectedFields[comparisonIndex] = {};
            }
            this.selectedFields[comparisonIndex][field] = {
                source,
                value,
            };
        },
        getButtonClass(field, source, comparisonIndex) {
            const isSelected = this.selectedFields[comparisonIndex]?.[field]?.source === source;
            return isSelected ? "bg-blue-500 text-white" : "bg-gray-200 hover:bg-gray-300";
        },
        getSelectedValue(field, comparisonIndex) {
            return this.selectedFields[comparisonIndex]?.[field]?.value ?? "";
        },

        async fetchDuplicate() {
            try {
                const response = await fetch("/admin/investors/get/duplicates", {
                    method: "GET",
                    headers: {
                        "Content-Type": "application/json",
                    },
                });

                if (response.ok) {
                    const data = await response.json();
                    this.comparisons = data.comparisons;
                } else {
                    console.error("Merge failed");
                }
            } catch (error) {
                console.error("Error during merge:", error);
            }
        },

        async mergeInvestors(comparisonIndex) {
            const mergedData = {
                investorA: this.comparisons[comparisonIndex].investorA.id,
                investorB: this.comparisons[comparisonIndex].investorB.id,
                selectedFields: this.selectedFields[comparisonIndex],
            };

            try {
                const response = await fetch("/api/investors/merge", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify(mergedData),
                });

                if (response.ok) {
                    this.comparisons.splice(comparisonIndex, 1);
                    delete this.selectedFields[comparisonIndex];
                } else {
                    console.error("Merge failed");
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
