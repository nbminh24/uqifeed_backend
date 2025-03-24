async def calculate_dish_calories(protein: float, fat: float, carbs: float) -> float:
    """
    Tính toán lượng calo của một món ăn dựa trên protein, fat và carbs.
    """
    return (protein * 4) + (fat * 9) + (carbs * 4)


async def calculate_total_nutrition(ingredients: list[dict]) -> dict:
    """
    Tính tổng dinh dưỡng (protein, fat, carbs) từ danh sách nguyên liệu.
    Mỗi nguyên liệu là một dictionary chứa protein, fat, carbs và amount.
    """
    total_protein = sum(ingredient["protein"] * ingredient["amount"] for ingredient in ingredients)
    total_fat = sum(ingredient["fat"] * ingredient["amount"] for ingredient in ingredients)
    total_carbs = sum(ingredient["carbs"] * ingredient["amount"] for ingredient in ingredients)

    return {
        "total_protein": total_protein,
        "total_fat": total_fat,
        "total_carbs": total_carbs
    }


async def calculate_meal_calories(dishes: list[dict]) -> float:
    """
    Tính tổng lượng calo của một bữa ăn dựa trên danh sách các món ăn.
    Mỗi món ăn là một dictionary chứa protein, fat và carbs.
    """
    total_calories = 0
    for dish in dishes:
        total_calories += await calculate_dish_calories(
            protein=dish["protein"],
            fat=dish["fat"],
            carbs=dish["carbs"]
        )
    return total_calories