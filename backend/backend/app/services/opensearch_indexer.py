from opensearchpy import OpenSearch, helpers
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.tables import Recipe

INDEX_ALIAS = "recipes_current"
INDEX_NAME = "recipes_v1"

MAPPING = {
    "mappings": {
        "properties": {
            "recipe_id": {"type": "keyword"},
            "source_recipe_id": {"type": "keyword"},
            "title": {"type": "text"},
            "dish": {"type": "keyword"},
            "quality_score": {"type": "float"},
            "rights_status": {"type": "keyword"},
            "takedown_status": {"type": "keyword"},
            "ingredients": {
                "type": "nested",
                "properties": {
                    "ingredient_id": {"type": "keyword"},
                    "canonical_name": {"type": "keyword"},
                    "required": {"type": "boolean"},
                    "position": {"type": "integer"},
                },
            },
            "step_summary": {"type": "text"},
        }
    }
}


def recipe_to_document(recipe: Recipe) -> dict:
    return {
        "recipe_id": str(recipe.id),
        "source_recipe_id": recipe.source_recipe_id,
        "title": recipe.title,
        "dish": recipe.dish,
        "quality_score": float(recipe.quality_score),
        "rights_status": recipe.rights_status,
        "takedown_status": recipe.takedown_status,
        "ingredients": [
            {
                "ingredient_id": str(item.ingredient_id) if item.ingredient_id else None,
                "canonical_name": item.canonical_name,
                "required": item.required,
                "position": item.position,
            }
            for item in recipe.ingredients
        ],
        "step_summary": " ".join(step.text for step in recipe.steps[:3]),
    }


def reindex_recipes(db: Session) -> dict:
    settings = get_settings()
    client = OpenSearch(settings.opensearch_url)

    if client.indices.exists(INDEX_NAME):
        client.indices.delete(INDEX_NAME)
    client.indices.create(INDEX_NAME, body=MAPPING)

    recipes = db.scalars(
        select(Recipe)
        .options(selectinload(Recipe.ingredients), selectinload(Recipe.steps))
        .where(Recipe.rights_status == "clear", Recipe.takedown_status == "active")
    ).all()

    actions = [
        {"_index": INDEX_NAME, "_id": recipe.id, "_source": recipe_to_document(recipe)}
        for recipe in recipes
    ]
    if actions:
        helpers.bulk(client, actions)

    if client.indices.exists_alias(name=INDEX_ALIAS):
        old_indices = list(client.indices.get_alias(name=INDEX_ALIAS).keys())
        client.indices.update_aliases(
            body={
                "actions": [{"remove": {"index": index, "alias": INDEX_ALIAS}} for index in old_indices]
                + [{"add": {"index": INDEX_NAME, "alias": INDEX_ALIAS}}]
            }
        )
    else:
        client.indices.put_alias(index=INDEX_NAME, name=INDEX_ALIAS)

    return {"index": INDEX_NAME, "alias": INDEX_ALIAS, "documents": len(actions)}
