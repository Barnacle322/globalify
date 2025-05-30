import os

import stripe


def get_or_create_stripe_product(expert):
    """Получает существующий или создает новый продукт Stripe для эксперта"""
    stripe.api_key = os.getenv("_STRIPE_SECRET_KEY")

    # Ищем существующий продукт
    products = stripe.Product.list(limit=100, active=True, expand=["data.default_price"])

    for product in products.data:
        if product.metadata.get("expert_id") == str(expert.id):
            return product.id

    # Создаем новый продукт если не найден
    product = stripe.Product.create(
        name=f"Expert Session: {expert.full_name}",
        description=expert.bio[:500] if expert.bio else f"Expert session with {expert.full_name}",
        metadata={
            "expert_id": str(expert.id),
            "expert_name": str(expert.full_name),
            "expert_email": str(expert.email),
            "type": "expert_session",
        },
        images=[expert.picture_url] if expert.picture_url else [],
        active=True,
    )
    return product.id


def get_or_create_stripe_price(product_id, amount):
    """Получает существующую или создает новую цену для продукта"""
    stripe.api_key = os.getenv("_STRIPE_SECRET_KEY")

    # Ищем существующую цену
    prices = stripe.Price.list(product=product_id, active=True, limit=10)

    # Ищем цену с нужной суммой
    for price in prices.data:
        if price.unit_amount == int(amount * 100):
            return price.id

    # Создаем новую цену
    price = stripe.Price.create(
        unit_amount=int(amount * 100),
        currency="usd",
        product=product_id,
    )
    return price.id
