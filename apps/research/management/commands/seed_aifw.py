"""Seed aifw providers, models, and action types for research-hub.

Usage:
    python manage.py seed_aifw          # idempotent create/update
    python manage.py seed_aifw --reset  # wipe + recreate
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

PROVIDERS = [
    {
        "name": "together_ai",
        "display_name": "Together AI",
        "api_key_env_var": "TOGETHER_API_KEY",
        "base_url": "https://api.together.xyz/v1",
    },
    {
        "name": "openai",
        "display_name": "OpenAI",
        "api_key_env_var": "OPENAI_API_KEY",
        "base_url": "",
    },
]

MODELS = [
    {
        "provider": "together_ai",
        "name": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "display_name": "Llama 3.3 70B Turbo",
        "max_tokens": 4096,
        "input_cost_per_million": "0.88",
        "output_cost_per_million": "0.88",
        "is_default": True,
    },
    {
        "provider": "together_ai",
        "name": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "display_name": "Llama 3.1 8B Turbo",
        "max_tokens": 2048,
        "input_cost_per_million": "0.18",
        "output_cost_per_million": "0.18",
    },
    {
        "provider": "openai",
        "name": "gpt-4.1",
        "display_name": "GPT-4.1",
        "max_tokens": 8192,
        "input_cost_per_million": "2.00",
        "output_cost_per_million": "8.00",
    },
    {
        "provider": "openai",
        "name": "gpt-4.1-mini",
        "display_name": "GPT-4.1 Mini",
        "max_tokens": 8192,
        "input_cost_per_million": "0.40",
        "output_cost_per_million": "1.60",
    },
]

ACTIONS = [
    {
        "code": "research.summarize",
        "name": "Recherche-Zusammenfassung",
        "description": (
            "Stufe 1: Zusammenfassung der Recherche-Ergebnisse. "
            "Schnelles Modell für initiale Synthese."
        ),
        "default_model": (
            "together_ai",
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        ),
        "fallback_model": (
            "together_ai",
            "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        ),
        "max_tokens": 2000,
        "temperature": 0.4,
    },
    {
        "code": "research.deep_analysis",
        "name": "Tiefenanalyse",
        "description": (
            "Stufe 2: Tiefenanalyse mit leistungsstarkem Modell. "
            "Kernaussagen, Widersprüche, Wissenslücken, "
            "Empfehlungen."
        ),
        "default_model": ("openai", "gpt-4.1"),
        "fallback_model": ("openai", "gpt-4.1-mini"),
        "max_tokens": 4000,
        "temperature": 0.3,
    },
    {
        "code": "research.reformat",
        "name": "Zusammenfassung umformatieren",
        "description": (
            "Text in anderes Format umwandeln "
            "(Stichpunkte, Fließtext, etc.)."
        ),
        "default_model": (
            "together_ai",
            "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        ),
        "fallback_model": (
            "together_ai",
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        ),
        "max_tokens": 600,
        "temperature": 0.3,
    },
]


class Command(BaseCommand):
    help = "Seed aifw providers, models, and action types."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing aifw data before seeding.",
        )

    def handle(self, *args, **options):
        from aifw.models import AIActionType, LLMModel, LLMProvider

        if options["reset"]:
            AIActionType.objects.all().delete()
            LLMModel.objects.all().delete()
            LLMProvider.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared all aifw data."))

        # --- Providers ---
        providers = {}
        for pdata in PROVIDERS:
            obj, created = LLMProvider.objects.update_or_create(
                name=pdata["name"],
                defaults={
                    "display_name": pdata["display_name"],
                    "api_key_env_var": pdata["api_key_env_var"],
                    "base_url": pdata.get("base_url", ""),
                    "is_active": True,
                },
            )
            providers[pdata["name"]] = obj
            tag = "Created" if created else "Updated"
            self.stdout.write(f"  {tag} provider: {obj.name}")

        # --- Models ---
        models = {}
        for mdata in MODELS:
            provider = providers[mdata["provider"]]
            obj, created = LLMModel.objects.update_or_create(
                provider=provider,
                name=mdata["name"],
                defaults={
                    "display_name": mdata["display_name"],
                    "max_tokens": mdata["max_tokens"],
                    "input_cost_per_million": mdata.get(
                        "input_cost_per_million", "0"
                    ),
                    "output_cost_per_million": mdata.get(
                        "output_cost_per_million", "0"
                    ),
                    "is_active": True,
                    "is_default": mdata.get("is_default", False),
                },
            )
            models[(mdata["provider"], mdata["name"])] = obj
            tag = "Created" if created else "Updated"
            self.stdout.write(f"  {tag} model: {obj.display_name}")

        # --- Actions ---
        for adata in ACTIONS:
            default = models[adata["default_model"]]
            fallback = models.get(adata.get("fallback_model"))
            defaults = {
                "name": adata["name"],
                "description": adata["description"],
                "default_model": default,
                "max_tokens": adata["max_tokens"],
                "temperature": adata["temperature"],
                "is_active": True,
            }
            if fallback:
                defaults["fallback_model"] = fallback
            obj, created = AIActionType.objects.update_or_create(
                code=adata["code"],
                defaults=defaults,
            )
            tag = "Created" if created else "Updated"
            self.stdout.write(
                f"  {tag} action: {obj.code} → {default.display_name}"
            )

        self.stdout.write(self.style.SUCCESS(
            f"\nDone: {len(PROVIDERS)} providers, "
            f"{len(MODELS)} models, {len(ACTIONS)} actions."
        ))
