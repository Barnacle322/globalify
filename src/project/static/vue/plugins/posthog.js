import posthog from "posthog-js";

export default {
    install(app) {
        app.config.globalProperties.$posthog = posthog.init("phc_OYnEo3PANvSj9HM4MFbRiG5IQVyhxw3iSZXxHUOI13F", {
            api_host: "https://us.i.posthog.com",
        });
    },
};
