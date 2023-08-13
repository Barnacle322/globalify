document.addEventListener('DOMContentLoaded', async () => {
    const { publishableKey } = await fetch('/payment/config').then((r) => r.json());
    const stripe = Stripe(publishableKey);

    const params = new URLSearchParams(window.location.href)
    const clientSecret = params.get('payment_intent_client_secret');

    const { paymentIntent } = stripe.retrievePaymentIntent(clientSecret).then((result) => {
        const paymentIntent = result.paymentIntent;
        const paymentIntentJson = JSON.stringify(paymentIntent, null, 2);

        document.querySelector('pre').textContent = paymentIntentJson;
    });
});